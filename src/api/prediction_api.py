
import os

from fastapi import Depends, FastAPI, HTTPException
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, Field

from src.api.securite import router, verifier_utilisateur
from src.models.predict import predire

class Logement(BaseModel):
    code_commune: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=1)

app = FastAPI(title="Compagnon Immobilier - Prediction")
app.include_router(router)

@app.post("/predict/")
def prediction(logement: Logement, user=Depends(verifier_utilisateur)):
    return predire(
        code_commune=logement.code_commune,
        type_local=logement.type_local,
        surface_reelle_bati=logement.surface_reelle_bati,
        nombre_pieces_principales=logement.nombre_pieces_principales,
    )


@app.get("/health")
def health():
    return {"status": "ok"}

# Endpoint pour de récupérer les infos de MLflow dans Streamlit
@app.get("/model-info")
def informations_modele(user=Depends(verifier_utilisateur)):
    # Lire dans MLflow les métadonnées du modèle avec l'alias champion
    try:
        client = MlflowClient(
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
        )
        champion = client.get_model_version_by_alias(
            name="compagnon_immobilier_xgboost", alias="champion",
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
            "metrics": metriques,
        }
    except MlflowException as erreur:
        raise HTTPException(
            status_code=503,
            detail="Impossible de lire le modèle Champion dans MLflow.",
        ) from erreur
