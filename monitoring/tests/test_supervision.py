"""Tests statiques et de non-régression des requêtes.

python monitoring/tests/test_supervision.py
PROMTOOL=/chemin/promtool python monitoring/tests/test_supervision.py
TEST_DATABASE_URL=postgresql://... : ajoute le test SQL transactionnel.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("generation", ROOT / "monitoring/generer_infrastructure.py")
generation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generation)


def verifier_artefacts_livres(racine=ROOT):
    """Lecture seule : échoue si un JSON livré manque ou diffère du générateur."""
    result = {}
    for expected_path, expected in generation.artefacts().items():
        relative = expected_path.relative_to(generation.ROOT)
        path = racine / "monitoring" / relative
        if not path.is_file():
            raise FileNotFoundError(f"Artefact à livrer absent : {path}")
        actual = json.loads(path.read_text(encoding="utf-8"))
        if actual != expected:
            raise ValueError(f"Artefact livré différent du générateur : {path}")
        result[str(relative)] = actual
    return result


class SupervisionTest(unittest.TestCase):
    def test_structure(self):
        compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
        services = compose["services"]
        for name in ["postgres-exporter", "node-exporter", "cadvisor", "statsd-exporter"]:
            self.assertIn(name, services)
            self.assertNotIn("ports", services[name])  # Aucun nouveau port public.
        for name in ["prediction_api", "training_api", "airflow-scheduler", "airflow-dag-processor"]:
            self.assertEqual(services[name]["depends_on"]["mlflow"]["condition"], "service_healthy")
        self.assertIn("--expose-prometheus", services["mlflow"]["command"][-1])
        self.assertEqual(compose["x-airflow-common"]["environment"]["AIRFLOW__METRICS__STATSD_DATADOG_ENABLED"], "true")
        config = yaml.safe_load((ROOT / "monitoring/prometheus/prometheus.yml").read_text())
        jobs = {job["job_name"] for job in config["scrape_configs"]}
        self.assertTrue({"postgres", "node", "cadvisor", "airflow_statsd", "mlflow_server", "minio"} <= jobs)

    def test_dashboard_and_alerts(self):
        shipped = verifier_artefacts_livres()
        dash = shipped["grafana/dashboards/infrastructure.json"]
        self.assertEqual(dash["uid"], "immo-infrastructure")
        self.assertEqual(len({p["id"] for p in dash["panels"]}), len(dash["panels"]))
        for panel in dash["panels"]:
            for target in panel["targets"]:
                # Les scores métier ne sont jamais présentés comme métriques du serveur MLflow.
                if 'job="mlflow_server"' in target["expr"]:
                    self.assertNotIn("ml_model_score", target["expr"])
                    self.assertIn("mlflow_http_request_duration_seconds", target["expr"])
        for rule in generation.RULES:
            self.assertRegex(rule["uid"], r"^[a-zA-Z0-9_-]{1,40}$")
        self.assertEqual(next(r for r in generation.RULES if r["uid"] == "immo-dag-failed")["no_data"], "OK")

    def test_missing_dashboard_is_not_recreated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "monitoring/grafana/dashboards/infrastructure.json"
            with self.assertRaises(FileNotFoundError):
                verifier_artefacts_livres(root)
            self.assertFalse(path.exists())

    def test_generator_in_isolated_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            # Seul ce test écrit des JSON: exclusivement dans son dossier temporaire.
            with patch.object(generation, "ROOT", Path(temp) / "monitoring"):
                generation.main()
                self.assertEqual(len(verifier_artefacts_livres(Path(temp))), 2)

    def test_sql_partition(self):
        metrics = yaml.safe_load((ROOT / "monitoring/sql_exporter/ml_monitoring.collector.yml").read_text())["metrics"]
        for metric in metrics:
            if "key_labels" in metric:
                self.assertIn("DISTINCT ON (metric_name, column_name, model_version)", metric["query"])
                self.assertIn("computed_at DESC, id DESC", metric["query"])

    @unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "TEST_DATABASE_URL non défini")
    def test_sql_latest_real_postgres(self):
        import psycopg
        metrics = yaml.safe_load((ROOT / "monitoring/sql_exporter/ml_monitoring.collector.yml").read_text())["metrics"]
        query = metrics[0]["query"].replace("monitoring.ml_metrics", "test_latest")
        with psycopg.connect(os.environ["TEST_DATABASE_URL"]) as conn:
            with conn.cursor() as cur:
                cur.execute("""CREATE TEMP TABLE test_latest (
                    id bigint, metric_name text, column_name text, model_version int,
                    computed_at timestamptz, value double precision)""")
                rows = [
                    (1, "drift_score", "surface", 1, "2026-11-01", 0.1),
                    (2, "drift_score", "surface", 2, "2026-11-02", 0.2),
                    (3, "drift_score", "surface", 1, "2026-11-03", 0.3),
                    (4, "drift_score", "surface", 1, "2026-11-03", 0.4),
                    (5, "drift_score", "pieces", 1, "2026-11-02", 0.5),
                    (6, "n_lignes", "", 1, "2026-11-02", 100),
                    (7, "n_lignes", "", 2, "2026-11-03", 200),
                ]
                cur.executemany("INSERT INTO test_latest VALUES (%s,%s,%s,%s,%s,%s)", rows)
                cur.execute(query)
                result = {(m, f, v): n for m, f, v, n in cur.fetchall()}
                self.assertEqual(len(result), 5)
                self.assertEqual(result[("drift_score", "surface", "1")], 0.4)
                self.assertEqual(result[("drift_score", "surface", "2")], 0.2)
            conn.rollback()

    def test_promql(self):
        tool = os.getenv("PROMTOOL") or shutil.which("promtool")
        if not tool:
            self.skipTest("promtool non disponible")
        subprocess.run([tool, "check", "config", str(ROOT / "monitoring/prometheus/prometheus.yml")], check=True)
        tests = yaml.safe_load((ROOT / "monitoring/tests/promql.yml").read_text())
        # La même expression sert à Grafana et aux tests : pas de copie divergente.
        for scenario in tests["tests"]:
            for check in scenario.get("promql_expr_test", []):
                if check["expr"].startswith("RULE:"):
                    uid = check["expr"][5:]
                    check["expr"] = next(r["expr"] for r in generation.RULES if r["uid"] == uid)
        # Parse aussi toutes les expressions de dashboards et toutes les alertes.
        expressions = [r["expr"] for r in generation.RULES]
        for path in (ROOT / "monitoring/grafana/dashboards").glob("*.json"):
            for panel in json.loads(path.read_text())["panels"]:
                expressions += [target["expr"] for target in panel.get("targets", []) if "expr" in target]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            rules = {"groups": [{"name": "syntax", "rules": [
                {"record": f"syntax_test_{i}", "expr": expr.replace("$__rate_interval", "2m")}
                for i, expr in enumerate(expressions)
            ]}]}
            (path / "syntax.yml").write_text(yaml.safe_dump(rules))
            subprocess.run([tool, "check", "rules", str(path / "syntax.yml")], check=True)
            (path / "tests.yml").write_text(yaml.safe_dump(tests))
            subprocess.run([tool, "test", "rules", str(path / "tests.yml")], check=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
