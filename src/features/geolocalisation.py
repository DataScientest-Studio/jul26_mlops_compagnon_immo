
"""Récupération des quartiers et calcul des coordonnées GPS."""

from functools import lru_cache

import requests
from geopy.distance import geodesic
from shapely.geometry import shape

WFS_URL = "https://data.geopf.fr/wfs/ows"
TYPE_COUCHE = "STATISTICALUNITS.IRIS:contours_iris"

# Même point de référence que dans build_features.py
LYON = (45.7640, 4.8357)


@lru_cache(maxsize=300)
def recuperer_quartiers(code_commune):
    """Récupère automatiquement les quartiers IRIS d'une commune."""

    code_commune = str(code_commune).zfill(5)

    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": TYPE_COUCHE,
        "OUTPUTFORMAT": "application/json",
        "SRSNAME": "EPSG:4326",
        "CQL_FILTER": f"code_insee='{code_commune}'",
        "COUNT": 500
    }

    response = requests.get(
        WFS_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()

    try:
        donnees = response.json()
    except ValueError as erreur:
        raise RuntimeError(
            "Réponse JSON invalide du service IGN"
        ) from erreur

    if donnees.get("type") != "FeatureCollection":
        raise RuntimeError("Réponse IGN inattendue")

    quartiers = []

    for feature in donnees.get("features", []):
        proprietes = feature.get("properties", {})
        geometrie = feature.get("geometry")

        if not geometrie:
            continue

        # Vérifier la commune
        if str(proprietes.get("code_insee")) != code_commune:
            continue

        # Code et nom du quartier
        code = proprietes.get("code_iris")
        nom = proprietes.get("nom_iris")

        if not code:
            continue

        # Point représentatif à l'intérieur du quartier
        point = shape(geometrie).representative_point()

        quartiers.append({
            "code_quartier": str(code),
            "nom_quartier": str(nom or code),
            "latitude": float(point.y),
            "longitude": float(point.x)
        })

    return sorted(
        quartiers,
        key=lambda q: q["nom_quartier"]
    )


def coordonnees_quartier(code_commune, code_quartier):
    # Retourne les coordonnées GPS du quartier choisi

    quartiers = recuperer_quartiers(code_commune)

    quartier = next(
        (
            q for q in quartiers
            if q["code_quartier"] == str(code_quartier)
        ),
        None
    )

    if quartier is None:
        raise ValueError("Quartier introuvable")

    return {
        "latitude": quartier["latitude"],
        "longitude": quartier["longitude"]
    }


def calculer_distance(latitude, longitude):
    # Calcule la distance jusqu'au centre de Lyon
    return geodesic(
        (latitude, longitude),
        LYON
    ).km
