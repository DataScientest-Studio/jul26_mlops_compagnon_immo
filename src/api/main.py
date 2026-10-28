
"""API FastAPI - Compagnon Immobilier."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.models.training import entrainer
from src.models.predict import predire
from typing import Literal
from fastapi import Form
from enum import Enum

class Communes(str, Enum):
    LYON_1 = "Lyon 1er — 69381"
    LYON_2 = "Lyon 2e — 69382"
    LYON_3 = "Lyon 3e — 69383"
    LYON_4 = "Lyon 4e — 69384"
    LYON_5 = "Lyon 5e — 69385"
    LYON_6 = "Lyon 6e — 69386"
    LYON_7 = "Lyon 7e — 69387"
    LYON_8 = "Lyon 8e — 69388"
    LYON_9 = "Lyon 9e — 69389"
    VILLEURBANNE = "Villeurbanne — 69266"
    VENISSIEUX = "Vénissieux — 69259"
    VAULX_EN_VELIN = "Vaulx-en-Velin — 69256"
    BRON = "Bron — 69029"
    CALUIRE_ET_CUIRE = "Caluire-et-Cuire — 69034"
    OULLINS = "Oullins — 69149"
    SAINT_PRIEST = "Saint-Priest — 69290"
    RILLIEUX_LA_PAPE = "Rillieux-la-Pape — 69286"
    DECINES_CHARPIEU = "Décines-Charpieu — 69275"


app = FastAPI(title="Compagnon Immobilier - MLOps")

# Modèle conservé en mémoire
modele_actuel = None

class Logement(BaseModel):
    code_commune: str
    type_local: str
    surface_reelle_bati: float = Field(gt=0)
    nombre_pieces_principales: int = Field(ge=0)


@app.post("/training/")
def training():
    global modele_actuel

    nouveau_modele, metriques = entrainer()
    modele_actuel = nouveau_modele

    return {
        "message": "Entraînement terminé",
        "metriques": metriques
    }


@app.post("/predict/")
def prediction(
    code_commune: Communes = Form(
        ..., description="Commune du Rhône"
    ),
    type_local: Literal["Maison", "Appartement"] = Form(
        ..., description="Type de logement"
    ),
    surface_reelle_bati: float = Form(
        60, gt=0, description="Surface habitable en m²"
    ),
    nombre_pieces_principales: int = Form(
        2, ge=0, description="Nombre de pièces"
    )
):
    if modele_actuel is None:
        raise HTTPException(
            status_code=503,
            detail="Lancer /training/ avant /predict/"
        )

    return predire(
        modele=modele_actuel,
        code_commune=code_commune.value.split(" — ")[-1],
        type_local=type_local,
        surface_reelle_bati=surface_reelle_bati,
        nombre_pieces_principales=nombre_pieces_principales
    )
