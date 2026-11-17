"""Génère uniquement le dashboard infrastructure et les alertes Grafana.

Usage: python monitoring/generer_infrastructure.py
Les trois dashboards métier ne sont pas régénérés par ce script.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DS = {"type": "prometheus", "uid": "prometheus"}

# Le modèle actif vient des métadonnées existantes, pas d'une version figée.
CHAMPION = 'ml_model_score{job="sql_exporter",score="mae",champion="true"}'
DRIFT = 'ml_monitoring_value{job="sql_exporter",metric="part_colonnes_en_drift",feature=""}'
DATE_DRIFT = (
    'ml_monitoring_computed_timestamp_seconds'
    '{job="sql_exporter",metric="part_colonnes_en_drift",feature=""}'
)
FAILED = (
    'airflow_dagrun_duration_seconds_count{job="airflow_statsd",state="failed",'
    'dag_id=~"training_immobilier|monitoring_evidently"}'
)

# Échec du DAG entier, après épuisement des retries, pas une tâche en retry.
# Le second terme détecte le premier événement d'une série nouvellement créée.
FAILED_EXPR = (
    f"sum by (dag_id) ((increase({FAILED}[15m]) > 0)"
    f" or (({FAILED} > 0) unless {FAILED} offset 15m))"
)

RULES = [
    dict(
        uid="immo-drift-champion", title="Drift du modèle champion",
        expr=f"max by (model_version) (({DRIFT} and on(model_version) {CHAMPION})"
             f" and on(model_version) ((time() - {DATE_DRIFT}) < 129600)) >= bool 0.5",
        evaluator="gt", threshold=0, pending="5m", no_data="OK", severity="warning",
        summary="Au moins 50 % des colonnes du champion sont en drift",
        description="Dernier calcul par version, âgé de moins de 36 h. "
                    "Le statut reste actif jusqu'au prochain calcul sain ou jusqu'à péremption.",
    ),
    dict(
        uid="immo-dag-failed", title="Échec d'un DAG immobilier",
        expr=FAILED_EXPR, evaluator="gt", threshold=0,
        pending="0s", no_data="OK", severity="critical",
        summary="Un DAG immobilier a terminé en échec dans les 15 dernières minutes",
        description="DAG : {{ $labels.dag_id }}. Vérifier les logs Airflow. "
                    "Événement StatsD non durable : voir les limites documentées.",
    ),
    dict(
        uid="immo-api-down", title="API de prédiction indisponible",
        expr='max(up{job="inference_api"}) or vector(0)',
        evaluator="lt", threshold=1, pending="2m", no_data="Alerting", severity="critical",
        summary="Prometheus ne peut plus lire /metrics de l'API depuis 2 minutes",
        description="Vérifier prediction_api, son réseau et MLflow. "
                    "Cette sonde ne valide pas une prédiction ni la présence d'un champion.",
    ),
    dict(
        uid="immo-statsd-down", title="Collecte StatsD Airflow indisponible",
        expr='max(up{job="airflow_statsd"}) or vector(0)',
        evaluator="lt", threshold=1, pending="2m", no_data="Alerting", severity="critical",
        summary="La collecte des événements Airflow est indisponible",
        description="Les échecs de DAG ne sont plus observables via StatsD. Vérifier statsd-exporter.",
    ),
    dict(
        uid="immo-scheduler-silent", title="Scheduler Airflow silencieux",
        expr='sum(increase(airflow_scheduler_heartbeat_total{job="airflow_statsd"}[3m])) or vector(0)',
        evaluator="lt", threshold=1, pending="5m", no_data="Alerting", severity="critical",
        summary="Aucun heartbeat Airflow récent",
        description="Le scheduler ou le flux DogStatsD est interrompu. "
                    "Le simple up de statsd-exporter ne garantit pas l'arrivée des événements.",
    ),
    dict(
        uid="immo-drift-stale", title="Monitoring du champion périmé",
        # Le champion est émis à zéro même avant son premier calcul de drift.
        expr=f"(time() - (max by(model_version) ({DATE_DRIFT})"
             f" or on(model_version) (max by(model_version) ({CHAMPION}) * 0)))"
             f" and on(model_version) {CHAMPION}",
        evaluator="gt", threshold=129600, pending="10m", no_data="OK", severity="warning",
        summary="Le champion n'a pas de mesure de drift fraîche (36 h)",
        description="Un DAG ignoré faute de prédictions n'est pas un échec. "
                    "Cette alerte indique une absence de mesure, pas une dérive. "
                    "Si aucune mesure n'existe pour le champion, elle s'active après 10 minutes.",
    ),
    dict(
        uid="immo-ml-collection-down", title="Collecte SQL des métriques ML indisponible",
        expr='max(up{job="sql_exporter"}) or vector(0)',
        evaluator="lt", threshold=1, pending="2m", no_data="Alerting", severity="critical",
        summary="Les mesures de drift et les scores métier ne sont plus collectés",
        description="Vérifier sql_exporter, PostgreSQL et les tables monitoring/metadata. "
                    "Ne pas interpréter l'absence de drift comme un état sain.",
    ),
]


def alert(rule):
    return {
        "uid": rule["uid"], "title": rule["title"], "condition": "C",
        "data": [
            {
                "refId": "A", "relativeTimeRange": {"from": 900, "to": 0},
                "datasourceUid": "prometheus",
                "model": {
                    "datasource": DS, "editorMode": "code", "expr": rule["expr"],
                    "instant": True, "range": False, "intervalMs": 1000,
                    "maxDataPoints": 43200, "refId": "A",
                },
            },
            {
                "refId": "C", "relativeTimeRange": {"from": 0, "to": 0},
                "datasourceUid": "__expr__",
                "model": {
                    "type": "threshold", "expression": "A", "refId": "C",
                    "conditions": [{
                        "type": "query",
                        "evaluator": {"type": rule["evaluator"], "params": [rule["threshold"]]},
                        "operator": {"type": "and"},
                        "reducer": {"type": "last", "params": []},
                        "query": {"params": ["C"]},
                    }],
                },
            },
        ],
        "noDataState": rule["no_data"], "execErrState": "Alerting",
        "for": rule["pending"], "isPaused": False,
        "annotations": {"summary": rule["summary"], "description": rule["description"]},
        "labels": {"project": "compagnon-immobilier", "severity": rule["severity"]},
    }


def panel(pid, title, expr, x, y, w=12, kind="timeseries", unit="short",
          legend="{{instance}}", description=""):
    return {
        "id": pid, "title": title, "type": kind, "description": description,
        "datasource": DS, "gridPos": {"x": x, "y": y, "w": w, "h": 8},
        "targets": [{
            "refId": "A", "datasource": DS, "expr": expr, "legendFormat": legend,
            "instant": kind == "stat", "range": kind != "stat",
        }],
        "fieldConfig": {
            "defaults": {
                "unit": unit, "min": 0,
                "color": {"mode": "palette-classic"},
                "thresholds": {"mode": "absolute", "steps": [{"value": None, "color": "green"}]},
            },
            "overrides": [],
        },
        "options": (
            {"reduceOptions": {"calcs": ["lastNotNull"], "values": False},
             "textMode": "auto", "colorMode": "value", "graphMode": "none"}
            if kind == "stat" else
            {"legend": {"displayMode": "table", "placement": "bottom", "showLegend": True},
             "tooltip": {"mode": "multi"}}
        ),
    }


def dashboard():
    definitions = [
        ("Disponibilité des cibles",
         'up{job=~"postgres|node|cadvisor|airflow_statsd|mlflow_server|minio|inference_api|sql_exporter"}',
         "short", "{{job}}", "up indique le succès de lecture des métriques, pas une disponibilité métier."),
        ("PostgreSQL : connexion à la base", 'pg_up{job="postgres"}',
         "short", "{{instance}}", "pg_up valide la connexion SQL, contrairement au simple up de l'exporter."),
        ("Hôte : CPU utilisé", '100 * (1 - avg by(instance) (rate(node_cpu_seconds_total{job="node",mode="idle"}[$__rate_interval])))',
         "percent", "{{instance}}", "Hôte Linux ou VM Docker Desktop, pas nécessairement le poste physique."),
        ("Hôte : mémoire utilisée", '100 * (1 - node_memory_MemAvailable_bytes{job="node"} / node_memory_MemTotal_bytes{job="node"})',
         "percent", "{{instance}}", ""),
        ("Hôte : systèmes de fichiers remplis",
         '100 * (1 - node_filesystem_avail_bytes{job="node",fstype!~"tmpfs|overlay|squashfs",device!~"rootfs"} / node_filesystem_size_bytes{job="node",fstype!~"tmpfs|overlay|squashfs",device!~"rootfs"})',
         "percent", "{{mountpoint}}", "Les points de montage Docker sont exclus côté Node Exporter."),
        ("Hôte : lectures disque",
         'rate(node_disk_read_bytes_total{job="node",device!~"loop.*|ram.*"}[$__rate_interval])',
         "Bps", "{{device}}", "Octets lus par seconde. Pas de graphe réseau hôte : Node Exporter utilise ici le réseau bridge Docker."),
        ("Conteneurs : cœurs CPU utilisés",
         'sum by(name) (rate(container_cpu_usage_seconds_total{job="cadvisor",name!=""}[$__rate_interval]))',
         "short", "{{name}}", "1 représente un cœur CPU utilisé. Métriques absentes si l'accès cgroup est refusé."),
        ("Conteneurs : mémoire active",
         'sum by(name) (container_memory_working_set_bytes{job="cadvisor",name!=""})',
         "bytes", "{{name}}", "Le compteur exclut une partie du cache récupérable."),
        ("Conteneurs : réseau reçu",
         'sum by(name) (rate(container_network_receive_bytes_total{job="cadvisor",name!="",interface!="lo"}[$__rate_interval]))',
         "Bps", "{{name}}", "Trafic reçu par les interfaces de chaque conteneur Docker."),
        ("Conteneurs : réseau émis",
         'sum by(name) (rate(container_network_transmit_bytes_total{job="cadvisor",name!="",interface!="lo"}[$__rate_interval]))',
         "Bps", "{{name}}", "Trafic émis par les interfaces de chaque conteneur Docker."),
        ("PostgreSQL : connexions",
         'sum by(datname,state) (pg_stat_activity_count{job="postgres",datname!=""})',
         "short", "{{datname}} / {{state}}", "Inclut les bases applicative, Airflow et MLflow visibles par le rôle."),
        ("PostgreSQL : taille des bases",
         'pg_database_size_bytes{job="postgres"}',
         "bytes", "{{datname}}", ""),
        ("PostgreSQL : transactions validées",
         'sum by(datname) (rate(pg_stat_database_xact_commit{job="postgres",datname!=""}[$__rate_interval]))',
         "ops", "{{datname}}", ""),
        ("PostgreSQL : deadlocks",
         'sum by(datname) (increase(pg_stat_database_deadlocks{job="postgres",datname!=""}[1h]))',
         "short", "{{datname}}", "Total glissant sur 1 h, ne pas sommer les points du graphe."),
        ("Airflow : heartbeat scheduler",
         'sum(rate(airflow_scheduler_heartbeat_total{job="airflow_statsd"}[$__rate_interval]))',
         "ops", "heartbeats/s", "Une série absente n'est pas remplacée artificiellement par zéro dans ce graphe."),
        ("Airflow : tâches en cours",
         'airflow_executor_running_tasks{job="airflow_statsd"}',
         "short", "en cours", ""),
        ("Airflow : tâches en attente",
         'airflow_executor_queued_tasks{job="airflow_statsd"}',
         "short", "en attente", ""),
        ("Airflow : échecs de DAG récents",
         FAILED_EXPR, "short", "{{dag_id}}", "Échecs terminaux observés dans les 15 dernières minutes."),
        ("MLflow serveur : requêtes HTTP",
         'sum by(status) (rate(mlflow_http_request_duration_seconds_count{job="mlflow_server"}[$__rate_interval]))',
         "reqps", "HTTP {{status}}", "Métriques de fonctionnement HTTP uniquement, pas MAE, RMSE ni R²."),
        ("MLflow serveur : latence HTTP p95",
         'histogram_quantile(0.95, sum by(le) (rate(mlflow_http_request_duration_seconds_bucket{job="mlflow_server"}[$__rate_interval])))',
         "s", "p95", "Ne couvre que les routes instrumentées du serveur, sans valider le stockage des artefacts."),
        ("MinIO : requêtes S3",
         'sum by(name) (rate(minio_api_requests_total{job="minio",type="s3"}[$__rate_interval]))',
         "reqps", "{{name}}", "API de métriques v3 ; voir la procédure si l'endpoint manque dans l'image installée."),
        ("MinIO : occupation des disques",
         '100 * minio_system_drive_used_bytes{job="minio"} / minio_system_drive_total_bytes{job="minio"}',
         "percent", "{{drive}}", "Occupation du système de fichiers, pas taille cumulée des seuls artefacts MLflow."),
    ]
    panels = [
        panel(i + 1, title, expr, (i % 2) * 12, (i // 2) * 8,
              unit=unit, legend=legend, description=desc)
        for i, (title, expr, unit, legend, desc) in enumerate(definitions)
    ]
    return {
        "uid": "immo-infrastructure", "title": "Infrastructure : hôte et services",
        "description": "PostgreSQL, hôte Linux, conteneurs, Airflow, MLflow serveur et MinIO. Aucun score métier d'entraînement.",
        "tags": ["infrastructure", "compagnon"], "timezone": "Europe/Paris",
        "schemaVersion": 41, "version": 1, "editable": True, "refresh": "30s",
        "time": {"from": "now-1h", "to": "now"}, "panels": panels,
        "templating": {"list": []}, "annotations": {"list": []},
    }


def artefacts():
    """Décrit les fichiers attendus sans les créer ni les modifier."""
    return {
        ROOT / "grafana/dashboards/infrastructure.json": dashboard(),
        ROOT / "grafana/provisioning/alerting/immobilier.json": {
            "apiVersion": 1,
            "groups": [{
                "orgId": 1, "name": "supervision-immobilier",
                "folder": "Compagnon Immobilier", "interval": "1m",
                "rules": [alert(rule) for rule in RULES],
            }],
        },
    }


def main():
    for path, content in artefacts().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
