"""Prédiction immobilière avec le modèle Champion MLflow."""

import logging
import os
import threading
import time
from datetime import datetime

import mlflow
import mlflow.pyfunc
import pandas as pd
from dotenv import load_dotenv
from mlflow import MlflowClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.features.geolocalisation import (
    coordonnees_quartier,
    calculer_distance
)

load_dotenv()

log = logging.getLogger(__name__)

NOM_MODELE = "compagnon_immobilier_xgboost"
ALIAS_CHAMPION = "champion"
MLFLOW_MODEL_URI = f"models:/{NOM_MODELE}@{ALIAS_CHAMPION}"   # conservé pour compatibilité
CARACTERISTIQUES = [ "code_commune", "type_local", "surface_reelle_bati", "nombre_pieces_principales", "latitude", "longitude", "distance_lyon_km", "surface_terrain", "nombre_lots", "annee_mutation", "niveau_vie_median", "densite_population"]

# Le champion n'est plus rechargé à chaque requête: on le garde en mémoire et on revérifie
# l'alias au plus toutes les DUREE_CACHE_S secondes (promotion prise en compte
# en moins d'une minute, sans redémarrer l'API).
DUREE_CACHE_S = float(os.getenv("CHAMPION_CACHE_SECONDS", "60"))

_verrou = threading.Lock()
_cache = {"modele": None, "version": None, "expire": 0.0}
_engine = None


class CommuneIntrouvable(ValueError):
    """Aucune transaction pour cette commune et ce type de logement."""


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
    return _engine


def champion():
    """Retourne (modèle, numéro de version) du champion.

    Le modèle est chargé par numéro de version et non par alias : la version journalisée
    dans prediction_logs est ainsi toujours celle qui a réellement répondu.
    """
    with _verrou:
        maintenant = time.monotonic()
        if _cache["modele"] is None or maintenant >= _cache["expire"]:
            try:
                mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
                version = int(MlflowClient().get_model_version_by_alias(NOM_MODELE, ALIAS_CHAMPION).version)
                if version != _cache["version"]:
                    _cache["modele"] = mlflow.pyfunc.load_model(f"models:/{NOM_MODELE}/{version}")
                    _cache["version"] = version
                    log.info("Champion chargé : V%s", version)
                _cache["expire"] = maintenant + DUREE_CACHE_S
            except Exception:
                if _cache["modele"] is None:
                    raise                      # rien à servir : l'erreur remonte (HTTP 503)
                log.exception("MLflow injoignable : on garde le champion V%s en mémoire", _cache["version"])
                _cache["expire"] = maintenant + 10
        return _cache["modele"], _cache["version"]


def predire(code_commune, type_local,
            surface_reelle_bati, nombre_pieces_principales,
            code_quartier, surface_terrain=None):

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


    # 4. Récupérer le Champion (en mémoire, rafraîchi périodiquement)
    modele, version = champion()

    # Copie des entrées exactes, avant le prétraitement interne du pipeline.
    # to_dict convertit les scalaires numpy; les valeurs manquantes deviennent SQL NULL.
    caracteristiques = {
        nom: None if pd.isna(valeur) else valeur
        for nom, valeur in logement.to_dict(orient="records")[0].items()
    }

    # 5. Effectuer la prédiction
    prix_m2 = float(modele.predict(logement)[0])

    return {
        "prix_m2_estime": round(prix_m2, 2),
        "valeur_totale_estimee": round(
            prix_m2 * surface_reelle_bati, 2
        ),
        "model_version": version,
        "caracteristiques": caracteristiques,  # contrat interne, retiré par l'API
    }
