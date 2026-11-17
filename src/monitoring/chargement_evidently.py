"""Chargement, côté Evidently, des artefacts enregistrés dans MLflow.

Utilisable depuis n'importe quel DAG/processus : seul MLFLOW_TRACKING_URI est
nécessaire (le serveur MLflow joue le rôle de proxy vers MinIO).
"""

import os
import tempfile

import mlflow
import mlflow.pyfunc
import pandas as pd
from mlflow import MlflowClient

NOM_MODELE = "compagnon_immobilier_xgboost"
ALIAS_CHAMPION = "champion"
DOSSIER_ARTEFACTS = "evidently"


def _client() -> MlflowClient:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    return MlflowClient()


def resoudre_version(version=None, alias=ALIAS_CHAMPION, nom_modele=NOM_MODELE) -> dict:
    """alias (ou numéro de version) -> version, run_id, id du dataset préparé."""
    client = _client()
    if version is not None:
        mv = client.get_model_version(nom_modele, str(version))
    else:
        mv = client.get_model_version_by_alias(nom_modele, alias)
    run = client.get_run(mv.run_id)
    return {
        "version": int(mv.version),
        "run_id": mv.run_id,
        "prepared_dataset_id": run.data.tags.get("prepared_dataset_id"),
        "model_name": nom_modele,
    }


def _lire_parquet(run_id: str, fichier: str) -> pd.DataFrame:
    _client()
    with tempfile.TemporaryDirectory() as tmp:
        chemin = mlflow.artifacts.download_artifacts(
            run_id=run_id, artifact_path=fichier, dst_path=tmp)
        return pd.read_parquet(chemin)   # lu en mémoire avant suppression du dossier


def charger_schema(run_id: str) -> dict:
    _client()
    return mlflow.artifacts.load_dict(f"runs:/{run_id}/{DOSSIER_ARTEFACTS}/schema.json")


def charger_reference(version=None, alias=ALIAS_CHAMPION):
    """Référence de drift du modèle (par défaut : le champion actuel)."""
    info = resoudre_version(version=version, alias=alias)
    return _lire_parquet(info["run_id"], f"{DOSSIER_ARTEFACTS}/reference_train.parquet"), charger_schema(info["run_id"]), info


def charger_jeu_test(version):
    """Assemble le test et les prédictions du candidat par identifiant de ligne."""
    info = resoudre_version(version=version)
    test = _lire_parquet(info["run_id"], "datasets/test_set.parquet")
    predictions = _lire_parquet(info["run_id"], "evaluation/predictions_candidat.parquet")
    schema = charger_schema(info["run_id"])
    for donnees in (test, predictions):
        if (donnees.index.name != "ligne_test"
                or not donnees.index.is_unique
                or donnees.index.hasnans):
            raise ValueError("Identifiants ligne_test absents, dupliqués ou nuls")
    if (len(test) != len(predictions)
            or not test.index.isin(predictions.index).all()):
        raise ValueError("Association test/prédictions invalide : lignes manquantes ou supplémentaires")
    if list(predictions.columns) != [schema["prediction"]]:
        raise ValueError("Le fichier des prédictions doit contenir uniquement la prédiction")
    return test.join(predictions, validate="one_to_one"), schema, info


def charger_modele(version=None, alias=ALIAS_CHAMPION, nom_modele=NOM_MODELE):
    """Pipeline complet (prétraitement + XGBoost) depuis le Registry."""
    _client()
    uri = f"models:/{nom_modele}/{version}" if version is not None else f"models:/{nom_modele}@{alias}"
    return mlflow.pyfunc.load_model(uri)


# --------------------------- Rapports -------------------------------------

def rapport_drift(reference: pd.DataFrame, courant: pd.DataFrame, schema: dict, metadata=None):
    """Drift production vs référence du champion (colonnes surveillées)."""
    from evidently import DataDefinition, Dataset, Report
    from evidently.presets import DataDriftPreset

    colonnes = schema["numerical"] + schema["categorical"]
    definition = DataDefinition(
        numerical_columns=schema["numerical"],
        categorical_columns=schema["categorical"],
    )
    ref = Dataset.from_pandas(reference[colonnes], data_definition=definition)
    cur = Dataset.from_pandas(courant[colonnes], data_definition=definition)
    return Report([DataDriftPreset()]).run(current_data=cur, reference_data=ref, metadata=metadata)

def rapport_qualite(courant: pd.DataFrame, metadata=None):
    """Qualité de régression : compare la prédiction à la vérité terrain observée."""
    from evidently import DataDefinition, Dataset, Regression, Report
    from evidently.presets import RegressionPreset

    donnees = courant[["target", "prediction"]].dropna().copy()
    if len(donnees) < 2:
        raise ValueError("Au moins deux lignes avec vérité terrain sont nécessaires pour le rapport qualité")

    definition = DataDefinition(
        regression=[Regression(target="target", prediction="prediction")]
    )
    dataset = Dataset.from_pandas(donnees, data_definition=definition)
    return Report([RegressionPreset()]).run(current_data=dataset, metadata=metadata)


def rapport_champion_vs_candidat(version_candidat: int):
    """Même jeu de test, deux modèles : référence = champion, courant = candidat."""
    from evidently import DataDefinition, Dataset, Regression, Report
    from evidently.presets import RegressionPreset

    test, schema, info = charger_jeu_test(version_candidat)
    champion = charger_modele(alias=ALIAS_CHAMPION)

    colonnes_modele = [c for c in test.columns if c not in (schema["target"], schema["prediction"])]
    pred_champion = champion.predict(test[colonnes_modele])

    definition = DataDefinition(regression=[Regression(target="target", prediction="prediction")])
    ref = Dataset.from_pandas(
        pd.DataFrame({"target": test[schema["target"]], "prediction": pred_champion}),
        data_definition=definition)
    cur = Dataset.from_pandas(
        test[[schema["target"], schema["prediction"]]].rename(
            columns={schema["target"]: "target", schema["prediction"]: "prediction"}),
        data_definition=definition)
    return Report([RegressionPreset()]).run(current_data=cur, reference_data=ref), info
