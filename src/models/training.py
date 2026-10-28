"""Entraînement XGBoost depuis PostgreSQL, sans sauvegarde du modèle."""
import os

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

load_dotenv()

CARACTERISTIQUES = [
    "code_commune", "type_local", "surface_reelle_bati", "nombre_pieces_principales", "latitude", "longitude", "distance_lyon_km", "surface_terrain", "nombre_lots", "annee_mutation", "niveau_vie_median", "densite_population"
]


def entrainer():
    """Retourne (pipeline entraîné, métriques JSON-compatibles)."""
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

    preprocesseur = ColumnTransformer([
        (
            "numeriques",
            SimpleImputer(strategy="median"),
            variables_numeriques
        ),
        (
            "categories",
            Pipeline([
                ("imputation", SimpleImputer(strategy="most_frequent")),
                ("encodage", OneHotEncoder(handle_unknown="ignore"))
            ]),
            variables_categorielles
        )
    ])
    
    # Pipeline XGBoost
    pipeline_xgb = Pipeline([
        ("pretraitement", preprocesseur),
        ("xgboost", XGBRegressor(
            objective="reg:squarederror",
            random_state=42,
            n_jobs=1
        ))
    ])

    # Hyperparamètres de ton ancien modèle optimisé 2
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
        random_state=42,
        n_jobs=1,
        verbose=1
    )

    recherche_xgb.fit(X_train, y_train)

    # Meilleur modèle
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
        # "meilleurs_parametres": {
        #     cle: float(valeur) if isinstance(valeur, np.floating)
        #     else int(valeur) if isinstance(valeur, np.integer)
        #     else valeur
        #     for cle, valeur in meilleurs_parametres.items()
        # }
    }

    return modele, metriques


if __name__ == "__main__":
    _, resultats = entrainer()
    print("Entraînement terminé (modèle non sauvegardé) :", resultats)
