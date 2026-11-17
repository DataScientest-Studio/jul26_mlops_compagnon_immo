"""Vérifications en lecture seule après démarrage de la stack.

python monitoring/verifier_supervision.py --prometheus http://localhost:9090
N'envoie aucune prédiction et ne déclenche aucun entraînement.
"""
import argparse
import json
from urllib.parse import urlencode
from urllib.request import urlopen

EXPECTED = {
    "postgres": "pg_up",
    "node": "node_cpu_seconds_total",
    "cadvisor": "container_cpu_usage_seconds_total",
    "airflow_statsd": "airflow_scheduler_heartbeat_total",
    "mlflow_server": "mlflow_exporter_info",
    "minio": "minio_api_requests_total",
    "sql_exporter": "ml_champion_version",
    "inference_api": "up",
}


def query(base, expression):
    with urlopen(base.rstrip("/") + "/api/v1/query?" + urlencode({"query": expression}), timeout=15) as response:
        result = json.load(response)
    if result["status"] != "success":
        raise RuntimeError(result)
    return result["data"]["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prometheus", default="http://localhost:9090")
    args = parser.parse_args()
    errors = 0
    for job, metric in EXPECTED.items():
        try:
            up = query(args.prometheus, f'up{{job="{job}"}}')
            if not up or any(float(row["value"][1]) != 1 for row in up):
                raise RuntimeError("cible absente ou collecte en échec (voir Prometheus /targets)")
            values = query(args.prometheus, f'{metric}{{job="{job}"}}')
            if not values:
                raise RuntimeError(f"collecte HTTP valide, mais métrique {metric} absente")
            if metric == "pg_up" and any(float(row["value"][1]) != 1 for row in values):
                raise RuntimeError("exporter joignable mais connexion PostgreSQL en échec")
            print(f"OK {job}: {metric}")
        except Exception as exc:
            errors += 1
            print(f"ÉCHEC {job}: {exc}")
    print("Une métrique MLflow/MinIO absente n'est pas assimilée à zéro.")
    print("Avant le premier entraînement, un champion à zéro est normal.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
