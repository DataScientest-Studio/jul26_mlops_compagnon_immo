"""Journal des prédictions : une ligne dans monitoring.prediction_logs par appel de /predict/.

C'est la source des « données courantes » du DAG de monitoring Evidently. L'insertion ne doit
jamais faire échouer une prédiction : toute erreur est journalisée et comptée (métrique
prediction_log_errors_total), pas propagée. Les erreurs de retour du prix réel remontent,
elles, à l'API pour que le formulaire n'annonce pas un succès non enregistré.
"""

import logging
import os
import threading
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)

_verrou = threading.Lock()
_engine = None


def _get_engine():
    global _engine
    with _verrou:
        if _engine is None:
            url = os.getenv("MONITORING_DATABASE_URL") or os.getenv("DATABASE_URL")
            if not url:
                raise RuntimeError("DATABASE_URL absent : impossible d'écrire le journal des prédictions")
            _engine = create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=2)
        return _engine


def enregistrer_prediction(request_id: str, model_version: int, caracteristiques: dict,
                           prix_m2_estime: float, valeur_totale_estimee: float,
                           erreurs=None) -> bool:
    """Retourne True si la ligne est écrite. `erreurs` : compteur Prometheus optionnel."""
    try:
        with _get_engine().begin() as cx:
            cx.execute(text("""
                INSERT INTO monitoring.prediction_logs
                    (created_at, request_id, model_version, code_commune, type_local,
                     surface_reelle_bati, nombre_pieces_principales, surface_terrain,
                     latitude, longitude, distance_lyon_km, nombre_lots, annee_mutation,
                     niveau_vie_median, densite_population, prix_m2_estime, valeur_totale_estimee)
                VALUES (:cree, :req, :version, :code_commune, :type_local,
                        :surface_reelle_bati, :nombre_pieces_principales, :surface_terrain,
                        :latitude, :longitude, :distance_lyon_km, :nombre_lots, :annee_mutation,
                        :niveau_vie_median, :densite_population, :prix, :total)
            """), {"cree": datetime.now(timezone.utc), "req": request_id, "version": int(model_version),
                   **caracteristiques, "prix": prix_m2_estime, "total": valeur_totale_estimee})
        return True
    except Exception:
        log.exception("Échec d'écriture dans monitoring.prediction_logs (request_id=%s)", request_id)
        if erreurs is not None:
            erreurs.inc()
        return False


def renseigner_prix_reel(request_id: str, prix_total_reel) -> dict:
    """Complète une ligne existante. Le verrou protège les soumissions concurrentes.

    LookupError : prédiction absente ; ValueError : retour différent déjà présent.
    Les erreurs de base remontent à l'endpoint.
    """
    with _get_engine().begin() as cx:
        ligne = cx.execute(text("""
            SELECT prix_total_reel, feedback_received_at
            FROM monitoring.prediction_logs
            WHERE request_id = :req
            FOR UPDATE
        """), {"req": request_id}).mappings().one_or_none()
        if ligne is None:
            raise LookupError("Prédiction introuvable")
        if ligne["prix_total_reel"] is not None:
            if ligne["prix_total_reel"] != prix_total_reel:
                raise ValueError("Un prix réel différent est déjà enregistré")
            return {"request_id": request_id, **dict(ligne)}

        retour = cx.execute(text("""
            UPDATE monitoring.prediction_logs
            SET prix_total_reel = :prix, feedback_received_at = now()
            WHERE request_id = :req
            RETURNING prix_total_reel, feedback_received_at
        """), {"req": request_id, "prix": prix_total_reel}).mappings().one()
        return {"request_id": request_id, **dict(retour)}
