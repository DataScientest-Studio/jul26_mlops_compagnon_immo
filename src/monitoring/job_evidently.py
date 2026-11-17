"""Job Evidently de monitoring (logique pure, sans dépendance à Airflow).

Production (monitoring.prediction_logs)  vs  référence du champion (artefact MLflow)
-> rapport Evidently (workspace + HTML) -> métriques dans monitoring.ml_metrics.
"""

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from src.monitoring.chargement_evidently import charger_reference, rapport_drift, rapport_qualite

log = logging.getLogger(__name__)

WORKSPACE_DIR = Path(os.getenv("EVIDENTLY_WORKSPACE", "/evidently_workspace"))
NOM_PROJET = "Compagnon Immo - Monitoring"
FENETRE_JOURS = int(os.getenv("MONITORING_WINDOW_DAYS", "7"))
MIN_LIGNES = int(os.getenv("MONITORING_MIN_ROWS", "100"))


def _engine():
    url = os.getenv("MONITORING_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("MONITORING_DATABASE_URL (ou DATABASE_URL) vers immobilier_db est absent")
    return create_engine(url, pool_pre_ping=True)


# ---------------------------- lecture -----------------------------------------

def calculer_fenetre(fin: datetime, jours: int = FENETRE_JOURS):
    fin = fin if fin.tzinfo else fin.replace(tzinfo=timezone.utc)
    return fin - timedelta(days=jours), fin


def compter_logs(version: int, debut: datetime, fin: datetime) -> int:
    engine = _engine()
    try:
        with engine.connect() as cx:
            return int(cx.execute(text("""
                SELECT COUNT(*) FROM monitoring.prediction_logs
                WHERE model_version = :v AND created_at >= :d AND created_at < :f
            """), {"v": version, "d": debut, "f": fin}).scalar_one())
    finally:
        engine.dispose()


def lire_logs(version: int, debut: datetime, fin: datetime) -> pd.DataFrame:
    """Entrées journalisées + prediction (EUR/m²) + retour facultatif (EUR)."""
    engine = _engine()
    try:
        with engine.connect() as cx:
            df = pd.read_sql_query(text("""
                SELECT code_commune, type_local, surface_reelle_bati,
                       nombre_pieces_principales, surface_terrain,
                       latitude, longitude, distance_lyon_km, nombre_lots, annee_mutation,
                       niveau_vie_median, densite_population,
                       prix_m2_estime AS prediction, prix_total_reel
                FROM monitoring.prediction_logs
                WHERE model_version = :v AND created_at >= :d AND created_at < :f
            """), cx, params={"v": version, "d": debut, "f": fin})
    finally:
        engine.dispose()
    df["code_commune"] = df["code_commune"].astype(str).str.zfill(5)
    for col in ("surface_reelle_bati", "nombre_pieces_principales", "surface_terrain",
                "latitude", "longitude", "distance_lyon_km", "nombre_lots", "annee_mutation",
                "niveau_vie_median", "densite_population", "prediction", "prix_total_reel"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ----------------------------- calcul -----------------------------------------

def extraire_metriques(snapshot, reference: pd.DataFrame, courant: pd.DataFrame) -> list[dict]:
    """Snapshot Evidently 0.7 -> liste de {metric_name, column_name, value}."""
    lignes = [
        {"metric_name": "n_lignes_courant", "column_name": "", "value": float(len(courant))},
        {"metric_name": "n_lignes_reference", "column_name": "", "value": float(len(reference))},
        {"metric_name": "prediction_moyenne_courant", "column_name": "", "value": float(courant["prediction"].mean())},
        {"metric_name": "prediction_moyenne_reference", "column_name": "", "value": float(reference["prediction"].mean())},
        {"metric_name": "prediction_ecart_type_courant", "column_name": "", "value": float(courant["prediction"].std())},
    ]
    nb_derive_calcule = 0
    for m in snapshot.dict()["metrics"]:
        type_metrique = m["config"].get("type", "").split(":")[-1]
        if type_metrique == "DriftedColumnsCount":
            lignes.append({"metric_name": "colonnes_en_drift", "column_name": "", "value": float(m["value"]["count"])})
            lignes.append({"metric_name": "part_colonnes_en_drift", "column_name": "", "value": float(m["value"]["share"])})
            nb_derive_attendu = int(m["value"]["count"])
        elif type_metrique == "ValueDrift":
            colonne, methode, seuil = m["config"]["column"], m["config"]["method"], m["config"]["threshold"]
            score = float(m["value"])
            # Tests statistiques (p-value) : drift si p < seuil ; distances : drift si distance >= seuil.
            en_drift = score < seuil if "p_value" in methode.lower() else score >= seuil
            nb_derive_calcule += int(en_drift)
            lignes.append({"metric_name": "drift_score", "column_name": colonne, "value": score})
            lignes.append({"metric_name": "drift_detecte", "column_name": colonne, "value": float(en_drift)})
    if "nb_derive_attendu" in locals() and nb_derive_attendu != nb_derive_calcule:
        log.warning("Incohérence drift : Evidently=%s, recalcul=%s (vérifier la règle de seuil)",
                    nb_derive_attendu, nb_derive_calcule)
    return lignes


def enregistrer_dans_workspace(snapshot, horodatage: datetime) -> str:
    """Workspace Evidently (volume persistant, consultable via Evidently UI) + copie HTML."""
    from evidently.ui.workspace import Workspace

    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    ws = Workspace.create(str(WORKSPACE_DIR / "workspace"))
    projet = next((p for p in ws.list_projects() if p.name == NOM_PROJET), None)
    if projet is None:
        projet = ws.create_project(NOM_PROJET)
        projet.save()
    ws.add_run(projet.id, snapshot)

    dossier_html = WORKSPACE_DIR / "html"
    dossier_html.mkdir(exist_ok=True)
    chemin = dossier_html / f"drift_{horodatage:%Y%m%dT%H%M%S}.html"
    snapshot.save_html(str(chemin))
    return str(chemin)


def executer_evidently(version: int, debut: datetime, fin: datetime) -> dict:
    """Compare la fenêtre de production à la référence du modèle `version`."""
    reference, schema, info = charger_reference(version=version)
    courant = lire_logs(version, debut, fin)
    if courant.empty:
        raise ValueError("Aucune prédiction dans la fenêtre : rien à comparer")

    metadata = {
        "model_name": info["model_name"],
        "model_version": str(info["version"]),
        "mlflow_run_id": info["run_id"],
        "prepared_dataset_id": str(info["prepared_dataset_id"] or "inconnu"),
        "window_start": debut.isoformat(),
        "window_end": fin.isoformat(),
    }

    # 1) Drift: uniquement les variables d'entrée, sans prediction ni target.
    snapshot = rapport_drift(reference, courant, schema, metadata={
        **metadata,
        "report_type": "drift",
        "reference_uri": f"runs:/{info['run_id']}/evidently/reference_train.parquet",
    })
    metriques = extraire_metriques(snapshot, reference, courant)
    html = enregistrer_dans_workspace(snapshot, fin)

    # 2) Qualité: uniquement les lignes pour lesquelles le prix réel est connu.
    # Même fenêtre basée sur created_at : pas de rattrapage des retours tardifs.
    valides = courant[["prediction", "prix_total_reel", "surface_reelle_bati"]].apply(
        lambda serie: serie.map(math.isfinite)
    ).all(axis=1)
    donnees_qualite = courant.loc[
        valides & courant["prix_total_reel"].gt(0) & courant["surface_reelle_bati"].gt(0)
    ].copy()
    donnees_qualite["target"] = (
        donnees_qualite["prix_total_reel"] / donnees_qualite["surface_reelle_bati"]
    )
    donnees_qualite = donnees_qualite.loc[donnees_qualite["target"].map(math.isfinite)]
    html_qualite = None
    nb_verites_terrain = int(len(donnees_qualite))
    #--------------------------------------------------------------------------------
    taux_verites_terrain = nb_verites_terrain / len(courant)

    metriques.append({
    "metric_name": "taux_verites_terrain",
    "column_name": "",
    "value": float(taux_verites_terrain)
    })
    #----------------------------------------------------------------------------------
    if nb_verites_terrain >= 2:
        snapshot_qualite = rapport_qualite(donnees_qualite, metadata={
            **metadata,
            "report_type": "quality",
            "source": "monitoring.prediction_logs",
        })
        html_qualite = enregistrer_dans_workspace(snapshot_qualite, fin)
    else:
        log.info("Rapport qualité ignoré : %s ligne(s) avec vérité terrain (minimum : 2)",
                 nb_verites_terrain)

    return {
        "version": info["version"],
        "prepared_dataset_id": info["prepared_dataset_id"],
        "metriques": metriques,
        "html": html,
        "html_qualite": html_qualite,
        "nb_verites_terrain": nb_verites_terrain,
    }
# ---------------------------------------------------------------------- export

def exporter_metriques(resultat: dict, dag_run_id: str, debut: datetime, fin: datetime) -> int:
    """Upsert idempotent dans monitoring.ml_metrics (un re-run ne crée pas de doublons)."""
    maintenant = datetime.now(timezone.utc)
    lignes = [{
        "computed_at": maintenant, "dag_run_id": dag_run_id,
        "model_version": resultat["version"], "prepared_dataset_id": resultat["prepared_dataset_id"],
        "window_start": debut, "window_end": fin, **m,
    } for m in resultat["metriques"]]

    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("""
                INSERT INTO monitoring.ml_metrics
                    (computed_at, dag_run_id, model_version, prepared_dataset_id,
                     window_start, window_end, metric_name, column_name, value)
                VALUES (:computed_at, :dag_run_id, :model_version, :prepared_dataset_id,
                        :window_start, :window_end, :metric_name, :column_name, :value)
                ON CONFLICT (dag_run_id, metric_name, column_name) DO UPDATE SET
                    computed_at = EXCLUDED.computed_at, value = EXCLUDED.value,
                    window_start = EXCLUDED.window_start, window_end = EXCLUDED.window_end
            """), lignes)
    finally:
        engine.dispose()
    return len(lignes)
