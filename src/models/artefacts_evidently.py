"""Artefacts MLflow destinés à Evidently : référence de drift et schéma."""

import tempfile
from pathlib import Path

import mlflow
import pandas as pd

# Les informations saisies par l'utilisateur complétés par les autres variables du modèle.
COLONNES_NUMERIQUES = [
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "surface_terrain",
    "latitude",
    "longitude",
    "distance_lyon_km",
    "nombre_lots",
    "niveau_vie_median",
    "densite_population",
]
COLONNES_CATEGORIELLES = ["code_commune", "type_local", "annee_mutation"]
COLONNES_SURVEILLEES = COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES

DOSSIER_ARTEFACTS = "evidently"          # dossier dans le run MLflow
TAILLE_MAX_REFERENCE = 20_000            # lignes max pour la référence de drift


def journaliser_artefacts_evidently(modele, X_train, X_test,
                                    prepared_dataset_id=None):
    """À appeler DANS le `with mlflow.start_run()` de training.py.

    Écrit dans le run actif :
      - evidently/reference_train.parquet : échantillon d'entraînement
        (4 entrées utilisateur + prédiction du modèle) -> référence du drift ;
      - evidently/schema.json : description des colonnes ;
      - tag prepared_dataset_id : lien avec le snapshot DVC / tables de métadonnées.
    """
    # 1. Référence de drift : échantillon du jeu d'entraînement
    echantillon = X_train
    if len(echantillon) > TAILLE_MAX_REFERENCE:
        echantillon = echantillon.sample(TAILLE_MAX_REFERENCE, random_state=42)
    reference = echantillon[COLONNES_SURVEILLEES].copy()
    reference["prediction"] = modele.predict(echantillon)

    schema = {
        "numerical": COLONNES_NUMERIQUES,
        "categorical": COLONNES_CATEGORIELLES,
        "prediction": "prediction",
        "target": "prix_m2",
        "nb_lignes_reference": int(len(reference)),
        "nb_lignes_test": int(len(X_test))
    }

    with tempfile.TemporaryDirectory() as tmp:
        reference.to_parquet(Path(tmp) / "reference_train.parquet", index=False)
        mlflow.log_artifacts(tmp, artifact_path=DOSSIER_ARTEFACTS)

    mlflow.log_dict(schema, f"{DOSSIER_ARTEFACTS}/schema.json")
    mlflow.set_tag("prepared_dataset_id", str(prepared_dataset_id or "inconnu"))
