"""DAG d'entraînement : données -> snapshots DVC -> PostgreSQL -> entraînement -> promotion.

  Tâche 1 - Données       collecter -> versionner_brut -> preparer -> versionner_prepare -> charger
  Tâche 2 - Entraînement  entrainer          (MLflow : paramètres, métriques, artefacts, Registry)
  Tâche 3 - Promotion     promouvoir         (rapport Evidently champion/candidat, alias champion)

Déclenchement manuel par défaut. Les données sont versionnées avec DVC.
"""

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, get_current_context, task, task_group


def _run_id() -> str:
    return get_current_context()["run_id"]


@dag(
    dag_id="training_immobilier",
    schedule=None,
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,       # un seul run à la fois : un seul dépôt DVC, une seule table chargée
    default_args={"retries": 1, "retry_delay": timedelta(minutes=5)},
    tags=["training", "dvc", "mlflow"],
)
def training_immobilier():

    @task_group(group_id="tache_1_donnees")
    def donnees():
        @task(execution_timeout=timedelta(hours=1))
        def collecter() -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.collecter(_run_id())

        @task
        def versionner_brut(collecte: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.versionner_brut(collecte, _run_id())

        @task(execution_timeout=timedelta(hours=1))
        def preparer(ids_bruts: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.preparer(ids_bruts, _run_id())

        @task
        def versionner_prepare(ids_bruts: dict, preparation: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.versionner_prepare(ids_bruts, preparation, _run_id())

        @task
        def charger(prepare: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.charger(prepare)

        collecte = collecter()
        ids_bruts = versionner_brut(collecte)
        preparation = preparer(ids_bruts)
        ids_bruts >> preparation          # la préparation lit les parquets bruts versionnés
        return charger(versionner_prepare(ids_bruts, preparation))

    @task_group(group_id="tache_2_entrainement")
    def entrainement(prepare: dict):
        @task(execution_timeout=timedelta(hours=3), retries=0)
        def entrainer(prepare: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.entrainer(prepare)

        return entrainer(prepare)

    @task_group(group_id="tache_3_promotion")
    def promotion(modele: dict):
        @task
        def promouvoir(modele: dict) -> dict:
            from src.pipeline import entrainement_etapes as e
            return e.promouvoir(modele)

        return promouvoir(modele)

    promotion(entrainement(donnees()))


training_immobilier()
