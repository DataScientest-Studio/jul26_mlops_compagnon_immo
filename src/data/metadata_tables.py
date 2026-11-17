"""Tables de métadonnées (schéma `metadata` de immobilier_db).

Le DDL est dans sql/02_metadata_schema.sql, complété par 04_metadata_git_dvc.sql
(appliqués au démarrage par le service db-init) ;
`creer_tables()` le rejoue par sécurité, ce qui permet aussi de lancer le DAG
sur une base qui n'a pas été initialisée par db-init.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, text

DOSSIER_SQL = Path(os.getenv("SQL_DIR", Path(__file__).resolve().parents[2] / "sql"))
FICHIERS_SQL = ["01_monitoring_schema.sql", "02_metadata_schema.sql", "04_metadata_git_dvc.sql"]


def _engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL absent : base immobilier_db non configurée")
    return create_engine(url, pool_pre_ping=True)


def _maintenant():
    return datetime.now(timezone.utc)


def creer_tables() -> None:
    engine = _engine()
    try:
        with engine.begin() as cx:
            for nom in FICHIERS_SQL:
                cx.exec_driver_sql(
                    (DOSSIER_SQL / nom).read_text(encoding="utf-8").replace("%", "%%"))
    finally:
        engine.dispose()


def enregistrer_brut(snap: dict, source: str, collected_at: datetime, source_url: str | None,
                     nb_lignes: int, dag_run_id: str | None = None) -> None:
    """Jeu brut identifié par le hash DVC du fichier final, métadonnées comprises."""
    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("""
                INSERT INTO metadata.raw_datasets
                    (id, source, collected_at, last_seen_at, source_url, nb_lignes,
                     taille_octets, chemin_dvc, uri_minio, dag_run_id,
                     dvc_git_commit, metadonnees)
                VALUES (:id, :source, :collecte, :collecte, :url, :nb, :taille, :chemin,
                        :uri, :run, :dvc_commit, CAST(:metadonnees AS JSONB))
                ON CONFLICT (id) DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
            """), {"id": snap["id"], "source": source, "collecte": collected_at, "url": source_url,
                   "nb": nb_lignes, "taille": snap["taille_octets"], "chemin": snap["chemin_dvc"],
                   "uri": snap["uri_minio"], "run": dag_run_id,
                   "dvc_commit": snap["dvc_git_commit"],
                   "metadonnees": json.dumps(snap["metadonnees"])})
    finally:
        engine.dispose()


def enregistrer_prepare(snap: dict, raw_dvf_id: str, raw_insee_id: str, nb_lignes: int,
                        dag_run_id: str | None = None) -> None:
    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("""
                INSERT INTO metadata.prepared_datasets
                    (id, created_at, nb_lignes, taille_octets, chemin_dvc, uri_minio,
                     raw_dvf_id, raw_insee_id, git_commit, dag_run_id, dvc_git_commit, metadonnees)
                VALUES (:id, :cree, :nb, :taille, :chemin, :uri, :dvf, :insee,
                        :commit, :run, :dvc_commit, CAST(:metadonnees AS JSONB))
                ON CONFLICT (id) DO NOTHING
            """), {"id": snap["id"],
                   "cree": datetime.fromisoformat(snap["metadonnees"]["prepared_at"]), "nb": nb_lignes,
                   "taille": snap["taille_octets"], "chemin": snap["chemin_dvc"],
                   "uri": snap["uri_minio"], "dvf": raw_dvf_id, "insee": raw_insee_id,
                   "commit": snap["metadonnees"].get("git_commit"), "run": dag_run_id,
                   "dvc_commit": snap["dvc_git_commit"],
                   "metadonnees": json.dumps(snap["metadonnees"])})
    finally:
        engine.dispose()


def enregistrer_chargement(table: str, prepared_dataset_id: str, nb_lignes: int) -> None:
    """Version du jeu préparé actuellement présente dans `table` (une ligne par table)."""
    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("""
                INSERT INTO metadata.loaded_tables (table_name, prepared_dataset_id, loaded_at, nb_lignes)
                VALUES (:t, :p, :l, :n)
                ON CONFLICT (table_name) DO UPDATE SET
                    prepared_dataset_id = EXCLUDED.prepared_dataset_id,
                    loaded_at = EXCLUDED.loaded_at, nb_lignes = EXCLUDED.nb_lignes
            """), {"t": table, "p": prepared_dataset_id, "l": _maintenant(), "n": nb_lignes})
    finally:
        engine.dispose()


def enregistrer_modele(version: int, run_id: str, prepared_dataset_id: str | None,
                       metriques: dict) -> None:
    """Version de modèle entraînée (tâche 2). La décision et le statut champion viennent de la tâche 3."""
    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("""
                INSERT INTO metadata.model_versions
                    (model_version, run_id, prepared_dataset_id, trained_at, nb_lignes,
                     mae, rmse, r2, mae_cv)
                VALUES (:v, :run, :p, :t, :n, :mae, :rmse, :r2, :mae_cv)
                ON CONFLICT (model_version) DO UPDATE SET
                    run_id = EXCLUDED.run_id, prepared_dataset_id = EXCLUDED.prepared_dataset_id,
                    nb_lignes = EXCLUDED.nb_lignes, mae = EXCLUDED.mae, rmse = EXCLUDED.rmse,
                    r2 = EXCLUDED.r2, mae_cv = EXCLUDED.mae_cv
            """), {"v": int(version), "run": run_id, "p": prepared_dataset_id, "t": _maintenant(),
                   "n": metriques.get("nb_lignes"), "mae": metriques.get("MAE"),
                   "rmse": metriques.get("RMSE"), "r2": metriques.get("R2"),
                   "mae_cv": metriques.get("MAE_CV")})
    finally:
        engine.dispose()


def enregistrer_decision(version: int, decision: str, version_champion: int) -> None:
    """Tâche 3 : décision de comparaison + bascule du statut champion (un seul à la fois)."""
    engine = _engine()
    try:
        with engine.begin() as cx:
            cx.execute(text("UPDATE metadata.model_versions SET decision = :d WHERE model_version = :v"),
                       {"d": decision, "v": int(version)})
            # En deux requêtes : l'index unique interdit deux champions, même un instant.
            cx.execute(text("UPDATE metadata.model_versions SET est_champion = FALSE "
                            "WHERE est_champion AND model_version <> :c"), {"c": int(version_champion)})
            cx.execute(text("UPDATE metadata.model_versions SET est_champion = TRUE, "
                            "promu_at = COALESCE(promu_at, now()) "
                            "WHERE model_version = :c AND NOT est_champion"), {"c": int(version_champion)})
    finally:
        engine.dispose()
