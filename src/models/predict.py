
"""Prédiction immobilière avec le modèle Champion MLflow."""

import os
from datetime import datetime

import mlflow
import mlflow.pyfunc
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.features.geolocalisation import (
    coordonnees_quartier,
    calculer_distance
)

load_dotenv()

MLFLOW_MODEL_URI = "models:/compagnon_immobilier_xgboost@champion"
CARACTERISTIQUES = [ "code_commune", "type_local", "surface_reelle_bati", "nombre_pieces_principales", "latitude", "longitude", "distance_lyon_km", "surface_terrain", "nombre_lots", "annee_mutation", "niveau_vie_median", "densite_population"]

def predire( code_commune, type_local, surface_reelle_bati, nombre_pieces_principales, code_quartier, surface_terrain=None):
    code_commune = str(code_commune).zfill(5)

    # Récupérer les coordonnées du quartier IRIS
    gps = coordonnees_quartier(code_commune, code_quartier)

    latitude = gps["latitude"]
    longitude = gps["longitude"]
    distance_lyon_km = calculer_distance(latitude, longitude)

    # Connexion PostgreSQL 
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        database_url = URL.create(
            drivername="postgresql+psycopg2",
            username=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="localhost",
            port=5433,
            database=os.getenv("POSTGRES_DB")
        )

    engine = create_engine(database_url)

    try:
        with engine.connect() as connexion:
            df = pd.read_sql_query(
                text("""
                    SELECT DISTINCT niveau_vie_median, densite_population
                    FROM public.transactions_immobilieres
                    WHERE code_commune = :code AND niveau_vie_median IS NOT NULL AND densite_population IS NOT NULL
                """),
                connexion,
                params={"code": code_commune}
            )
    finally:
        engine.dispose()

    if df.empty:
        raise ValueError(
            "Indicateurs INSEE indisponibles pour cette commune"
        )

    if len(df) != 1:
        raise ValueError(
            "Plusieurs valeurs INSEE trouvées pour cette commune"
        )

    niveau_vie_median = float(df.iloc[0]["niveau_vie_median"])
    densite_population = float(df.iloc[0]["densite_population"])

    # Gérer la surface du terrain
    if type_local == "Appartement":
        surface_terrain = None
    elif surface_terrain is not None:
        surface_terrain = float(surface_terrain)

    # Construire les caractéristiques du modèle (correspond à l'entraînement)
    logement = pd.DataFrame([{
        "code_commune": code_commune,
        "type_local": type_local,
        "surface_reelle_bati": surface_reelle_bati,
        "nombre_pieces_principales": nombre_pieces_principales,
        "latitude": latitude,
        "longitude": longitude,
        "distance_lyon_km": distance_lyon_km,
        "surface_terrain": surface_terrain,
        "nombre_lots": 1 if type_local == "Appartement" else 0,
        "annee_mutation": datetime.now().year,
        "niveau_vie_median": niveau_vie_median,
        "densite_population": densite_population
    }])[CARACTERISTIQUES]

    # Charger le Champion MLflow
    mlflow.set_tracking_uri( os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))

    modele = mlflow.pyfunc.load_model(MLFLOW_MODEL_URI)

    # Effectuer la prédiction
    prix_m2 = float(modele.predict(logement)[0])

    return {
        "prix_m2_estime": round(prix_m2, 2),
        "valeur_totale_estimee": round(
            prix_m2 * surface_reelle_bati, 2
        )
    }
