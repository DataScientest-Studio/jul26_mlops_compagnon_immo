"""Vérifie les JSON directement dans un ZIP, sans extraction ni génération.

python monitoring/tests/verifier_archive.py chemin/vers/immo_patch.zip
N'utilise que la bibliothèque standard Python.
"""
import argparse
import json
from pathlib import PurePosixPath
import zipfile


DASHBOARDS = {
    "api_prediction.json": "api-prediction",
    "ml_drift.json": "ml-drift",
    "pipeline_modeles.json": "ml-pipeline",
    "infrastructure.json": "immo-infrastructure",
}


def verifier_archive(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Intégrité ZIP incorrecte")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Entrées ZIP dupliquées")
        # Accepte le dossier enveloppe du patch ou une archive sans enveloppe.
        suffix = "monitoring/grafana/dashboards/infrastructure.json"
        matches = [name for name in names if name == suffix or name.endswith("/" + suffix)]
        if len(matches) != 1:
            raise ValueError("infrastructure.json absent ou ambigu dans le ZIP")
        prefix = matches[0][:-len(suffix)]
        checked = []
        for filename, uid in DASHBOARDS.items():
            name = prefix + "monitoring/grafana/dashboards/" + filename
            if name not in names:
                raise ValueError(f"Dashboard absent du ZIP : {name}")
            data = json.loads(archive.read(name))
            if data.get("uid") != uid or not data.get("panels"):
                raise ValueError(f"Dashboard invalide : {name}")
            checked.append(f"{filename} : {len(data['panels'])} panneaux")
        alert_name = prefix + "monitoring/grafana/provisioning/alerting/immobilier.json"
        if alert_name not in names:
            raise ValueError("Règles Grafana absentes du ZIP")
        alerts = json.loads(archive.read(alert_name))
        rules = [rule for group in alerts.get("groups", []) for rule in group.get("rules", [])]
        required_uids = {"immo-drift-champion", "immo-dag-failed", "immo-api-down"}
        if not required_uids <= {rule.get("uid") for rule in rules}:
            raise ValueError("Une des trois alertes demandées est absente")
        checked.append(f"immobilier.json : {len(rules)} règles")
        for name in names:
            if ".." in PurePosixPath(name).parts or PurePosixPath(name).is_absolute():
                raise ValueError(f"Chemin ZIP non sûr : {name}")
        return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args()
    try:
        checked = verifier_archive(args.archive)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ÉCHEC : {exc}\n")
    for item in checked:
        print("OK " + item)
    print("Archive vérifiée sans extraction ni génération.")


if __name__ == "__main__":
    main()
