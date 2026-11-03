
from fastapi import FastAPI
from src.models.predict import predire
from pydantic import BaseModel, Field

class Logement(BaseModel):
    code_commune: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=1)

app = FastAPI(title="Compagnon Immobilier - Prediction")


@app.post("/predict/")
def prediction(logement: Logement):
    return predire(
        code_commune=logement.code_commune,
        type_local=logement.type_local,
        surface_reelle_bati=logement.surface_reelle_bati,
        nombre_pieces_principales=logement.nombre_pieces_principales,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
