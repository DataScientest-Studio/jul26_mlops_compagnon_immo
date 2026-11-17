"""API de prédiction immobilière avec authentification OAuth2/JWT."""

import logging
import time
import uuid
from decimal import Decimal
from uuid import UUID



import os

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from src.api.journal_predictions import enregistrer_prediction, renseigner_prix_reel
from src.api.securite import router, verifier_utilisateur
from src.models.predict import CommuneIntrouvable, predire
from src.features.geolocalisation import recuperer_quartiers



log = logging.getLogger(__name__)


class Logement(BaseModel):
    code_commune: str
    code_quartier: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=1)
    surface_terrain: float | None = Field(default=None, ge=0)


class PrixReel(BaseModel):
    prix_total_reel: Decimal = Field(gt=0, allow_inf_nan=False)

# --- Métriques Prometheus (exposées sur GET /metrics) -------------------------------------
HTTP_REQUETES = Counter("http_requests_total", "Requêtes HTTP", ["method", "path", "status"])
HTTP_LATENCE = Histogram("http_request_duration_seconds", "Durée des requêtes HTTP", ["method", "path"])
PREDICTIONS = Counter("predictions_total", "Prédictions servies", ["model_version", "type_local"])
PREDICTION_ERREURS = Counter("prediction_errors_total", "Prédictions en échec", ["type"])
PRIX_M2 = Histogram("prediction_prix_m2_estime", "Prix au m2 estimé (EUR)",
                    buckets=[1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 6000, 7000, 8000, 10000])
JOURNAL_ERREURS = Counter("prediction_log_errors_total",
                          "Échecs d'écriture dans monitoring.prediction_logs")

app = FastAPI(title="Compagnon Immobilier - Prediction")
app.include_router(router)

@app.middleware("http")
async def mesurer_http(request: Request, call_next):
    debut = time.perf_counter()
    statut = 500
    try:
        reponse = await call_next(request)
        statut = reponse.status_code
        return reponse
    finally:
        route = request.scope.get("route")
        chemin = route.path if route is not None else "inconnu"   # évite l'explosion des labels
        if chemin != "/metrics":
            HTTP_REQUETES.labels(request.method, chemin, str(statut)).inc()
            HTTP_LATENCE.labels(request.method, chemin).observe(time.perf_counter() - debut)


@app.post("/predict/")
def prediction(logement: Logement, taches: BackgroundTasks, user=Depends(verifier_utilisateur)):
    try:
        resultat = predire(
            code_commune=logement.code_commune,
            code_quartier=logement.code_quartier,
            type_local=logement.type_local,
            surface_reelle_bati=logement.surface_reelle_bati,
            nombre_pieces_principales=logement.nombre_pieces_principales,
            surface_terrain=logement.surface_terrain
        )

    except CommuneIntrouvable as exc:
        PREDICTION_ERREURS.labels("commune_introuvable").inc()
        raise HTTPException(status_code=404, detail=str(exc))
    except MlflowException as exc:
        PREDICTION_ERREURS.labels("modele_indisponible").inc()
        log.exception("Champion indisponible")
        raise HTTPException(status_code=503, detail="Modèle champion indisponible") from exc
    except Exception:
        PREDICTION_ERREURS.labels("erreur_interne").inc()
        raise

    request_id = str(uuid.uuid4())
    resultat["request_id"] = request_id
    PREDICTIONS.labels(str(resultat["model_version"]), logement.type_local).inc()
    PRIX_M2.observe(resultat["prix_m2_estime"])

    # Journal au mieux en arrière-plan : le Request ID ne garantit pas la persistance.
    caracteristiques = resultat.pop("caracteristiques")
    taches.add_task(
        enregistrer_prediction,
        request_id=request_id,
        model_version=resultat["model_version"],
        caracteristiques=caracteristiques,
        prix_m2_estime=resultat["prix_m2_estime"],
        valeur_totale_estimee=resultat["valeur_totale_estimee"],
        erreurs=JOURNAL_ERREURS,
    )
    return resultat


@app.put("/predictions/{request_id}/prix-reel")
def ajouter_prix_reel(request_id: UUID, retour: PrixReel,
                      user=Depends(verifier_utilisateur)):
    # Même autorisation user/admin que /predict/ ; pas de propriété par utilisateur
    # dans le journal actuel de cette application de démonstration.
    try:
        return renseigner_prix_reel(str(request_id), retour.prix_total_reel)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail="Prédiction introuvable : vérifiez le Request ID. "
                   "L'enregistrement peut être en attente ou avoir échoué.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (SQLAlchemyError, RuntimeError) as exc:
        log.exception("Échec d'enregistrement du prix réel (request_id=%s)", request_id)
        raise HTTPException(status_code=503, detail="Journal des prédictions indisponible") from exc


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Endpoint pour de récupérer les infos de MLflow dans Streamlit
@app.get("/model-info")
def informations_modele(user=Depends(verifier_utilisateur)):
    # Lire dans MLflow les métadonnées du modèle avec l'alias champion
    try:
        client = MlflowClient(
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        )

        champion = client.get_model_version_by_alias(
            name="compagnon_immobilier_xgboost",
            alias="champion"
        )

        metriques = (
            client.get_run(champion.run_id).data.metrics
            if champion.run_id else {}
        )

        return {
            "modele": champion.name,
            "alias": "champion",
            "version": champion.version,
            "run_id": champion.run_id,
            "metrics": metriques
        }

    except MlflowException as erreur:
        raise HTTPException(
            status_code=503,
            detail="Impossible de lire le modèle Champion dans MLflow."
        ) from erreur


@app.get("/quartiers/{code_commune}")
def quartiers_commune(code_commune: str):
    # Récupère les quartiers IRIS 

    try:
        quartiers = recuperer_quartiers(code_commune)

        return [
            {
                "code_quartier": q["code_quartier"],
                "nom_quartier": q["nom_quartier"]
            }
            for q in quartiers
        ]

    except (requests.RequestException, RuntimeError) as erreur:
        raise HTTPException(
            status_code=503,
            detail="Service géographique indisponible"
        ) from erreur
