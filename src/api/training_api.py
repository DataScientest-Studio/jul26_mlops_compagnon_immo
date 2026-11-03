
from fastapi import FastAPI
from src.models.training import entrainer

app = FastAPI(title="Compagnon Immobilier - Training")


@app.post("/training/")
def training():
    _, metriques = entrainer()
    return {"message": "Entraînement terminé", "metriques": metriques}


@app.get("/health")
def health():
    return {"status": "ok"}
