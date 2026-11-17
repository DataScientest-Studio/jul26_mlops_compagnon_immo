"""DAG de monitoring : production (prediction_logs) vs référence du champion (MLflow).

Tâches :
  1. verifier_donnees: résout le champion, compte les prédictions de la fenêtre,
                          saute le run s'il y en a trop peu ;
  2. calculer_evidently: charge la référence MLflow, lance le rapport de drift,
                          l'enregistre dans le workspace Evidently ;
  3. exporter_metriques: écrit les métriques dans immobilier_db (monitoring.ml_metrics),
                          que sql_exporter expose à Prometheus.

Le rapport est enregistré dans Evidently et les métriques dans PostgreSQL.
Le traitement est ignoré si le nombre de prédictions est insuffisant. (MONITORING_MIN_ROWS dans docker-compose.yml)
Les imports lourds (mlflow, evidently...) sont faits dans les tâches pour garder
un parsing du DAG rapide.
"""

from datetime import datetime, timezone

from airflow.sdk import dag, get_current_context, task
from airflow.sdk.exceptions import AirflowSkipException


def _fenetre():
    from src.monitoring.job_evidently import calculer_fenetre

    ctx = get_current_context()
    run = ctx["dag_run"]
    fin = ctx.get("data_interval_end") or getattr(run, "run_after", None) or datetime.now(timezone.utc)
    return calculer_fenetre(fin)


@dag(
    dag_id="monitoring_evidently",
    schedule="0 6 * * *",                      # tous les jours à 06:00
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 1},
    tags=["monitoring", "evidently"]
)
def monitoring_evidently():

    @task
    def verifier_donnees() -> dict:
        from src.monitoring.chargement_evidently import resoudre_version
        from src.monitoring.job_evidently import MIN_LIGNES, compter_logs

        debut, fin = _fenetre()
        champion = resoudre_version()            # alias champion -> version / run
        n = compter_logs(champion["version"], debut, fin)
        if n < MIN_LIGNES:
            raise AirflowSkipException(
                f"{n} prédictions pour le champion V{champion['version']} "
                f"sur la fenêtre (minimum {MIN_LIGNES}) : monitoring ignoré.")
        return {"version": champion["version"], "n_logs": n,
                "debut": debut.isoformat(), "fin": fin.isoformat()}

    @task
    def calculer_evidently(fenetre: dict) -> dict:
        from src.monitoring.job_evidently import executer_evidently

        return executer_evidently(
            version=fenetre["version"],
            debut=datetime.fromisoformat(fenetre["debut"]),
            fin=datetime.fromisoformat(fenetre["fin"])
        )

    @task
    def exporter_metriques(resultat: dict, fenetre: dict) -> int:
        from src.monitoring.job_evidently import exporter_metriques as exporter

        return exporter(
            resultat, dag_run_id=get_current_context()["run_id"],
            debut=datetime.fromisoformat(fenetre["debut"]),
            fin=datetime.fromisoformat(fenetre["fin"])
        )

    fenetre = verifier_donnees()
    resultat = calculer_evidently(fenetre)
    exporter_metriques(resultat, fenetre)


monitoring_evidently()
