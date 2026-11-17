"""Entraînement XGBoost depuis PostgreSQL avec suivi MLflow."""

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from scipy.stats import randint, uniform
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor
import mlflow
import mlflow.sklearn
from mlflow.store.artifact.mlflow_artifacts_repo import MlflowArtifactsRepository
import hashlib
from src.models.comparer_model import selectionner_champion
from src.models.artefacts_evidently import journaliser_artefacts_evidently
 
load_dotenv()

CARACTERISTIQUES = [
    "code_commune", "type_local", "surface_reelle_bati", "nombre_pieces_principales", "latitude", "longitude", "distance_lyon_km", "surface_terrain", "nombre_lots", "annee_mutation", "niveau_vie_median", "densite_population"
]


def entrainer(prepared_dataset_id=None, promouvoir=True):
    """Retourne (pipeline entraîné, métriques JSON-compatibles).

    prepared_dataset_id : ID (hash DVC) du jeu préparé utilisé, fourni par la
    tâche 1 du DAG (tables de métadonnées).
    promouvoir : True (défaut, comportement historique, utilisé par training_api) compare
    et promeut le candidat dans la foulée ; False dans le DAG d'entraînement, où la
    comparaison est la tâche 3 (src/models/promotion.py).
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL absent dans le fichier .env")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connexion:
            df = pd.read_sql_query(
                text("SELECT * FROM public.transactions_immobilieres"),
                connexion,
            )
    finally:
        engine.dispose()

    if df.empty:
        raise ValueError("La table transactions_immobilieres est vide")

    variables_numeriques = [
        col for col in CARACTERISTIQUES
        if col not in ["code_commune", "type_local"]
    ]

    variables_categorielles = [
        "code_commune",
        "type_local"
    ]

    df["code_commune"] = df["code_commune"].astype("string").str.zfill(5).astype(object)
    df["type_local"] = df["type_local"].astype("string").astype(object)
    for col in variables_numeriques + ["prix_m2"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["prix_m2", "surface_reelle_bati", "type_local", "code_commune"])
    df = df.loc[(df["prix_m2"] > 0) & (df["surface_reelle_bati"] > 0)]
    if len(df) < 10:
        raise ValueError("Pas assez de données valides pour entraîner le modèle")

    X = df[CARACTERISTIQUES]
    y = df["prix_m2"] 
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=X["type_local"]
    )

    # Empreinte des données utilisées pour garder la tracabilité
    donnees_test = X_test.copy()
    donnees_test["cible_prix_m2"] = y_test

    empreinte = pd.util.hash_pandas_object(donnees_test, index=True).values.tobytes()
    evaluation_id = hashlib.sha256(empreinte).hexdigest()

    preprocesseur = ColumnTransformer([("numeriques", SimpleImputer(strategy="median"), variables_numeriques)
                            , ("categories", Pipeline([ ("imputation", SimpleImputer(strategy="most_frequent")), ("encodage", OneHotEncoder(handle_unknown="ignore"))]), variables_categorielles)])
    
    # Pipeline XGBoost
    pipeline_xgb = Pipeline([("pretraitement", preprocesseur),
        ("xgboost", XGBRegressor(objective="reg:squarederror", random_state=42, n_jobs=1))
    ])

    # Hyperparamètres du modèle xgboost 
    parametres = {
        "xgboost__n_estimators": randint(700, 901),
        "xgboost__learning_rate": uniform(0.05, 0.02),
        "xgboost__max_depth": [6, 7, 8],
        "xgboost__min_child_weight": [1, 2, 3],
        "xgboost__subsample": uniform(0.75, 0.15),
        "xgboost__colsample_bytree": uniform(0.75, 0.15),
        "xgboost__reg_alpha": uniform(0.10, 0.20),
        "xgboost__reg_lambda": uniform(1.8, 1.2),
        "xgboost__gamma": uniform(0.05, 0.15)
    }

    # Optimisation
    recherche_xgb = RandomizedSearchCV(
        estimator=pipeline_xgb,
        param_distributions=parametres,
        n_iter=20,
        scoring="neg_mean_absolute_error",
        cv=3,
        # random_state=42,
        n_jobs=1,
        verbose=1
    )

    recherche_xgb.fit(X_train, y_train)

    modele = recherche_xgb.best_estimator_
    meilleurs_parametres = recherche_xgb.best_params_
    mae_cv = -recherche_xgb.best_score_

    y_pred = modele.predict(X_test)

    metriques = {
        "nb_lignes": int(len(df)),
        "MAE": round(float(mean_absolute_error(y_test, y_pred)), 2),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 2),
        "R2": round(float(r2_score(y_test, y_pred)), 4),
        "MAE_CV": round(float(mae_cv), 2),
    }

    # Configuration MLflow
    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    )

    mlflow.set_experiment("compagnon_immobilier")

    with mlflow.start_run(run_name="xgboost_training") as run:

        # Enregistrer les hyperparamètres
        mlflow.log_params(meilleurs_parametres)

        # Enregistrer les métriques
        mlflow.log_metrics(metriques)

        # Identifier le jeu d'évaluation
        mlflow.log_param("evaluation_id", evaluation_id)
# ------------------------------------------------------------------------------------------
        # Déclarer les datasets utilisés par ce run dans MLflow.
        for nom, contexte, fichier, X_partie, y_partie in (
            ("transactions_train", "training", "train_set.parquet", X_train, y_train),
            ("transactions_test", "testing", "test_set.parquet", X_test, y_test),
        ):
            donnees = X_partie.reset_index(drop=True).copy()
            donnees["prix_m2"] = y_partie.to_numpy()
            if contexte == "testing":
                donnees.index.name = "ligne_test"

            with tempfile.TemporaryDirectory() as tmp:
                chemin = Path(tmp) / fichier
                donnees.to_parquet(chemin, index=(contexte == "testing"))
                mlflow.log_artifact(str(chemin), artifact_path="datasets")

            source = mlflow.get_artifact_uri(f"datasets/{fichier}")
            # MLflow 3.16.1 ne résout pas mlflow-artifacts: comme source de dataset.
            if source.startswith("mlflow-artifacts:"):
                source = MlflowArtifactsRepository.resolve_uri(
                    source, mlflow.get_tracking_uri()
                )

            dataset = mlflow.data.from_pandas(
                donnees,
                source=source,
                name=nom,
                targets="prix_m2",
            )

            mlflow.log_input(
                dataset,
                context=contexte,
                tags={
                    "prepared_dataset_id": str(
                        prepared_dataset_id or "inconnu"
                    ),
                },
            )

        predictions = pd.DataFrame({"prediction": y_pred})
        predictions.index.name = "ligne_test"
        with tempfile.TemporaryDirectory() as tmp:
            chemin = Path(tmp) / "predictions_candidat.parquet"
            predictions.to_parquet(chemin, index=True)
            mlflow.log_artifact(str(chemin), artifact_path="evaluation")
# ------------------------------------------------------------------------------------------
        # Artefacts pour Evidently (référence de drift + schéma) et lien DVC
        journaliser_artefacts_evidently(
            modele=modele,
            X_train=X_train,
            X_test=X_test,
            prepared_dataset_id=prepared_dataset_id,
        )

        # Enregistrer le modèle dans le Registry
        model_info = mlflow.sklearn.log_model(
            sk_model=modele,
            name="xgboost_model",
            registered_model_name="compagnon_immobilier_xgboost",
            serialization_format="skops",
            skops_trusted_types=[
                "numpy.dtype",
                "xgboost.core.Booster",
                "xgboost.sklearn.XGBRegressor"
            ]
        )

        version = model_info.registered_model_version

        if version is None:
            raise RuntimeError(
                "Le modèle n'a pas été enregistré dans le Registry"
            )

        # Comparer automatiquement (sauf si la promotion est déléguée à la tâche 3 du DAG)
        if promouvoir:
            decision = selectionner_champion(
                version=version,
                nouvelle_mae=mean_absolute_error(y_test, y_pred),
                X_test=X_test,
                y_test=y_test
            )
            print(f"MLflow - Version {version} : {decision}")
            metriques["comparaison"] = decision

        metriques["version_mlflow"] = int(version)
        metriques["run_id"] = run.info.run_id

    return modele, metriques


if __name__ == "__main__":
    _, resultats = entrainer()
    print("Entraînement terminé et modèle enregistré dans MLflow :", resultats)
