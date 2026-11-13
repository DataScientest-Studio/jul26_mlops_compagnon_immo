"""Sélection automatique du meilleur modèle MLflow."""

import mlflow.pyfunc
from mlflow import MlflowClient
from sklearn.metrics import mean_absolute_error

NOM_MODELE = "compagnon_immobilier_xgboost"

def selectionner_champion(version, nouvelle_mae, X_test, y_test):
    client = MlflowClient()

    # Vérifier si un Champion existe déjà
    modele_enregistre = client.get_registered_model(NOM_MODELE)
    numero_champion = modele_enregistre.aliases.get("champion")

    # Premier entraînement : définir automatiquement le Champion
    if numero_champion is None:
        client.set_registered_model_alias(
            NOM_MODELE, "champion", str(version)
        )
        return f"Premier Champion défini : V{version}"

    # Récupérer le Champion actuel
    champion = client.get_model_version(
        NOM_MODELE, str(numero_champion)
    )

    if str(champion.version) == str(version):
        return f"Version V{version} déjà Champion"

    # Charger le modèle Champion précédent depuis MLflow
    ancien_modele = mlflow.pyfunc.load_model(
        f"models:/{NOM_MODELE}@champion"
    )

    # Réévaluer l'ancien modèle sur le même jeu de test
    anciennes_predictions = ancien_modele.predict(X_test)
    ancienne_mae = mean_absolute_error(y_test, anciennes_predictions)

    # Comparer les performances
    if nouvelle_mae < ancienne_mae:
        client.set_registered_model_alias(
            NOM_MODELE, "champion", str(version)
        )
        return f"Nouveau Champion V{version}"

    return f"Champion V{champion.version} conservé"