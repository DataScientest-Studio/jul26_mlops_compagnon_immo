
from fastapi import FastAPI, Depends
from src.models.training import entrainer
from src.api.securite import router, verifier_admin

app = FastAPI(title="Compagnon Immobilier - Training")
app.include_router(router)


@app.post("/training/")
def training(user=Depends(verifier_admin)):
    _, metriques = entrainer()
    return {"message": "Entraînement terminé", "metriques": metriques}


@app.get("/health")
def health():
    return {"status": "ok"}
