import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.api.prediction_api import app, Logement

from types import SimpleNamespace
from unittest.mock import Mock
import src.models.comparer_model as comparer_model

client = TestClient(app)


# Test 1 : Surface invalide
@pytest.mark.parametrize("surface", [-10, 0])
def test_surface_invalide(surface):
    with pytest.raises(ValidationError):
        Logement(
            code_commune="69383",
            type_local="Appartement",
            surface_reelle_bati=surface,
            nombre_pieces_principales=3
        )


# Test 2 : Nombre de pièces invalide
def test_nombre_pieces_invalide():
    with pytest.raises(ValidationError):
        Logement(
            code_commune="69383",
            type_local="Appartement",
            surface_reelle_bati=70,
            nombre_pieces_principales=0
        )


# Test 3 : API disponible
def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Test 4 : Prédiction sans authentification
def test_prediction_sans_token():
    logement = {
        "code_commune": "69383",
        "type_local": "Appartement",
        "surface_reelle_bati": 70,
        "nombre_pieces_principales": 3
    }

    response = client.post("/predict/", json=logement)
    assert response.status_code == 401

# Test 5 : l'attribution de l'alias Champion à un premier modèle
def test_premier_champion(monkeypatch):
    # Simuler MLflow sans connexion au serveur
    faux_client = Mock()
    faux_client.get_registered_model.return_value = (
        SimpleNamespace(aliases={})
    )

    monkeypatch.setattr(
        comparer_model, "MlflowClient",
        lambda: faux_client
    )

    # Sélectionner le premier Champion
    resultat = comparer_model.selectionner_champion(
        version=1,
        nouvelle_mae=650,
        X_test=None,
        y_test=None
    )

    assert resultat == "Premier Champion défini : V1"

    faux_client.set_registered_model_alias.assert_called_once_with(
        "compagnon_immobilier_xgboost", "champion", "1"
    )
