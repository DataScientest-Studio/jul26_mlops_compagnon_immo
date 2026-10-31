
"""Prédiction immobilière avec le modèle Champion MLflow."""

import os
from datetime import datetime

import mlflow
import mlflow.pyfunc
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

MLFLOW_MODEL_URI = "models:/compagnon_immobilier_xgboost@champion"

def predire(code_commune, type_local,
            surface_reelle_bati, nombre_pieces_principales):

    code_commune = str(code_commune).zfill(5)

    # 1. Récupérer les variables supplémentaires depuis PostgreSQL
    engine = create_engine(os.getenv("DATABASE_URL"))

    with engine.connect() as connexion:
        df = pd.read_sql_query(
            text("""
                SELECT latitude, longitude, distance_lyon_km,
                       surface_terrain, nombre_lots,
                       niveau_vie_median, densite_population
                FROM public.transactions_immobilieres
                WHERE code_commune = :code
                    AND type_local = :type
            """),
            connexion,
            params={"code": code_commune, "type": type_local}
        )

    if df.empty:
        raise ValueError("Commune ou type de logement introuvable")

    valeurs = df.median(numeric_only=True).to_dict()

    # 3. Construire les 12 variables du modèle
    logement = pd.DataFrame([{
        "code_commune": code_commune,
        "type_local": type_local,
        "surface_reelle_bati": surface_reelle_bati,
        "nombre_pieces_principales": nombre_pieces_principales,
        **valeurs,
        "annee_mutation": datetime.now().year
    }])

    # 4. Charger le Champion depuis MLflow
    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )
    modele = mlflow.pyfunc.load_model(MLFLOW_MODEL_URI)

    # 5. Effectuer la prédiction
    prix_m2 = float(modele.predict(logement)[0])

    return {
        "prix_m2_estime": round(prix_m2, 2),
        "valeur_totale_estimee": round(
            prix_m2 * surface_reelle_bati, 2
        )
    }
