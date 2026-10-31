
"""API FastAPI - Compagnon Immobilier."""

from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel, Field

from src.models.training import entrainer
from src.models.predict import predire
from typing import Literal
from enum import Enum

class Logement(BaseModel):
    code_commune: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=1)

app = FastAPI(title="Compagnon Immobilier - MLOps")

@app.post("/training/")
def training():

    _, metriques = entrainer()

    return {
        "message": "Entraînement terminé",
        "metriques": metriques
    }

@app.post("/predict/")
def prediction(logement: Logement):
    return predire(
        code_commune=logement.code_commune,
        type_local=logement.type_local,
        surface_reelle_bati=logement.surface_reelle_bati,
        nombre_pieces_principales=logement.nombre_pieces_principales
    )