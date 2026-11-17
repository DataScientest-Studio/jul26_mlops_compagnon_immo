"""Étapes du DAG d'entraînement (logique pure, testable sans Airflow).

Chaque étape reçoit et renvoie seulement de petites valeurs JSON (IDs, compteurs) : les
jeux de données passent d'une tâche à l'autre par le dépôt Git/DVC partagé, jamais
par la mémoire, puisque chaque tâche Airflow est un processus distinct.

  Tâche 1  collecter -> versionner_brut -> preparer -> versionner_prepare -> charger
  Tâche 2  entrainer
  Tâche 3  promouvoir
"""

import logging
import os
from datetime import datetime, timezone

from src.data import metadata_tables as meta
from src.data import versionnement_dvc as dvc

log = logging.getLogger(__name__)

CHEMIN_DVF = "raw/dvf.parquet"
CHEMIN_INSEE = "raw/insee.parquet"
CHEMIN_PREPARE = "prepared/transactions_immobilieres.parquet"
TABLE_CHARGEE = "public.transactions_immobilieres"


# ----------------------------------------------------------------- tâche 1

def collecter(dag_run_id: str) -> dict:
    """run_pipeline.py, étape 2 : DVF + INSEE -> parquet dans le dépôt DVC (pas encore versionnés)."""
    from src.data.collecte import DVF_URL, INSEE_URL, collecter as collecter_sources

    meta.creer_tables()
    git_commit = os.getenv("GIT_COMMIT") or dvc._commande("git", "rev-parse", "HEAD")
    dvf, insee = collecter_sources()
    collected_at = datetime.now(timezone.utc).isoformat()
    for source, df, chemin, url in (("dvf", dvf, CHEMIN_DVF, DVF_URL),
                                    ("insee", insee, CHEMIN_INSEE, INSEE_URL)):
        dvc.ecrire_parquet(df, chemin, {
            "source": source, "source_url": url, "collected_at": collected_at,
            "dag_run_id": dag_run_id, "nb_lignes": int(len(df)), "git_commit": git_commit})
    return {"collected_at": collected_at,
            "dvf_url": DVF_URL, "insee_url": INSEE_URL,
            "nb_dvf": int(len(dvf)), "nb_insee": int(len(insee))}


def versionner_brut(collecte: dict, dag_run_id: str) -> dict:
    """Snapshot DVC des deux jeux bruts (MinIO) + métadonnées. L'ID vient du hash DVC :
    on enregistre donc les métadonnées après le snapshot, pas avant."""
    collected_at = datetime.fromisoformat(collecte["collected_at"])
    ids = {}
    for source, chemin, url, nb in (("dvf", CHEMIN_DVF, collecte["dvf_url"], collecte["nb_dvf"]),
                                    ("insee", CHEMIN_INSEE, collecte["insee_url"], collecte["nb_insee"])):
        snap = dvc.versionner_fichier(chemin)
        meta.enregistrer_brut(snap, source, collected_at, url, nb, dag_run_id)
        ids[f"raw_{source}_id"] = snap["id"]
    return ids


def preparer(ids_bruts: dict, dag_run_id: str) -> dict:
    """Nettoyage, features, jointure DVF + INSEE (pretraitement.py / build_features.py)."""
    from src.data.pretraitement import pretraiter

    dataset = pretraiter(dvc.lire_parquet(CHEMIN_DVF), dvc.lire_parquet(CHEMIN_INSEE))
    sources = {source: dvc.lire_metadonnees(chemin)
               for source, chemin in (("dvf", CHEMIN_DVF), ("insee", CHEMIN_INSEE))}
    dvc.ecrire_parquet(dataset, CHEMIN_PREPARE, {
        "source": "dvf+insee", "sources": sources,
        "prepared_at": datetime.now(timezone.utc).isoformat(), "dag_run_id": dag_run_id,
        "raw_dvf_id": ids_bruts["raw_dvf_id"], "raw_insee_id": ids_bruts["raw_insee_id"],
        "nb_lignes": int(len(dataset)), "git_commit": sources["dvf"].get("git_commit")})
    return {"nb_lignes": int(len(dataset))}


def versionner_prepare(ids_bruts: dict, preparation: dict, dag_run_id: str) -> dict:
    """Snapshot DVC du jeu préparé + métadonnées (liées aux deux jeux bruts par clés étrangères)."""
    snap = dvc.versionner_fichier(CHEMIN_PREPARE)
    meta.enregistrer_prepare(snap, ids_bruts["raw_dvf_id"], ids_bruts["raw_insee_id"],
                             preparation["nb_lignes"], dag_run_id)
    return {"prepared_dataset_id": snap["id"], "nb_lignes": preparation["nb_lignes"]}


def charger(prepare: dict) -> dict:
    """load_database.py : le jeu préparé (relu depuis DVC) remplace public.transactions_immobilieres."""
    from src.data.load_database import charger as charger_table, creer_base

    creer_base()
    charger_table(dvc.lire_parquet(CHEMIN_PREPARE))
    meta.enregistrer_chargement(TABLE_CHARGEE, prepare["prepared_dataset_id"], prepare["nb_lignes"])
    return prepare


# ----------------------------------------------------------------- tâche 2

def entrainer(prepare: dict) -> dict:
    """training.py sur la table qui vient d'être chargée. La promotion est laissée à la tâche 3."""
    from src.models.training import entrainer as entrainer_modele

    _, metriques = entrainer_modele(prepared_dataset_id=prepare["prepared_dataset_id"],
                                    promouvoir=False)
    meta.enregistrer_modele(metriques["version_mlflow"], metriques["run_id"],
                            prepare["prepared_dataset_id"], metriques)
    return {"version": metriques["version_mlflow"], "run_id": metriques["run_id"],
            "MAE": metriques["MAE"], "R2": metriques["R2"],
            "prepared_dataset_id": prepare["prepared_dataset_id"]}


# ----------------------------------------------------------------- tâche 3

def promouvoir(modele: dict) -> dict:
    from src.models.promotion import promouvoir_candidat

    resultat = promouvoir_candidat(modele["version"])
    meta.enregistrer_decision(resultat["version"], resultat["decision"], resultat["version_champion"])
    return resultat
