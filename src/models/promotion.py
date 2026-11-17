"""Tâche 3 du DAG d'entraînement : comparaison champion / candidat et promotion.

Ne dépend que de MLflow (serveur + artefacts) : le jeu de test et les prédictions du candidat
ont été enregistrés dans les artefacts du run lors de l'entraînement, donc cette
tâche peut tourner dans un autre processus que l'entraînement, sans rien avoir en mémoire.
"""

import logging
import tempfile
from pathlib import Path

from mlflow import MlflowClient
from sklearn.metrics import mean_absolute_error

from src.models.comparer_model import selectionner_champion
from src.monitoring.chargement_evidently import (
    ALIAS_CHAMPION, NOM_MODELE, charger_jeu_test, rapport_champion_vs_candidat,
)

log = logging.getLogger(__name__)


def version_champion():
    """Numéro de version du champion actuel, ou None s'il n'y en a pas encore."""
    modele = MlflowClient().get_registered_model(NOM_MODELE)
    numero = modele.aliases.get(ALIAS_CHAMPION)
    return int(numero) if numero is not None else None


def _journaliser_rapport_evidently(version: int, run_id: str) -> bool:
    """Rapport de régression champion vs candidat (même jeu de test), joint au run du candidat."""
    try:
        snapshot, _ = rapport_champion_vs_candidat(version)
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "champion_vs_candidat.html"
            snapshot.save_html(str(html))
            MlflowClient().log_artifact(run_id, str(html), "evidently")
        return True
    except Exception:       # le rapport ne doit pas bloquer la promotion
        log.exception("Rapport Evidently champion/candidat non généré (V%s)", version)
        return False


def promouvoir_candidat(version: int) -> dict:
    """Compare le candidat `version` au champion sur le jeu de test du candidat, puis promeut si meilleur.

    Retourne {version, decision, version_champion, mae_candidat, rapport_evidently}.
    """
    test, schema, info = charger_jeu_test(version)
    cible, prediction = schema["target"], schema["prediction"]
    X_test, y_test = test.drop(columns=[cible, prediction]), test[cible]
    mae_candidat = float(mean_absolute_error(y_test, test[prediction]))

    # Rapport avant la décision : « champion » désigne alors encore l'ancien champion.
    rapport = False
    if version_champion() not in (None, int(version)):
        rapport = _journaliser_rapport_evidently(int(version), info["run_id"])

    decision = selectionner_champion(
        version=version, nouvelle_mae=mae_candidat, X_test=X_test, y_test=y_test)
    champion = version_champion()
    log.info("Promotion V%s : %s (champion actuel V%s)", version, decision, champion)
    return {"version": int(version), "decision": decision, "version_champion": champion,
            "mae_candidat": round(mae_candidat, 4), "rapport_evidently": rapport}
