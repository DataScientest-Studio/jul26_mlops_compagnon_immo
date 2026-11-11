
"""API de prédiction immobilière avec authentification OAuth2/JWT."""

import os

import requests
from fastapi import Depends, FastAPI, HTTPException
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, Field

from src.api.securite import router, verifier_utilisateur
from src.models.predict import predire
from src.features.geolocalisation import recuperer_quartiers


class Logement(BaseModel):
    code_commune: str
    code_quartier: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=1)
    surface_terrain: float | None = Field(default=None, ge=0)


app = FastAPI(title="Compagnon Immobilier - Prediction")
app.include_router(router)


@app.post("/predict/")
def prediction(
    logement: Logement,
    user=Depends(verifier_utilisateur)
):
    try:
        return predire(
            code_commune=logement.code_commune,
            code_quartier=logement.code_quartier,
            type_local=logement.type_local,
            surface_reelle_bati=logement.surface_reelle_bati,
            nombre_pieces_principales=logement.nombre_pieces_principales,
            surface_terrain=logement.surface_terrain
        )

    except (requests.RequestException, RuntimeError) as erreur:
        raise HTTPException(
            status_code=503,
            detail="Service géographique temporairement indisponible"
        ) from erreur

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model-info")
def informations_modele(user=Depends(verifier_utilisateur)):
    try:
        client = MlflowClient(
            tracking_uri=os.getenv(
                "MLFLOW_TRACKING_URI",
                "http://mlflow:5000"
            )
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
