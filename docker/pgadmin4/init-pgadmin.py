import json
import os
from pathlib import Path
import sys


for variable in ("POSTGRES_USER", "POSTGRES_DB"):
    if not os.environ.get(variable):
        raise SystemExit(f"Variable absente : {variable}")


serveurs = {
    "Servers": {
        "1": {
            "Name": "Compagnon — PostgreSQL",
            "Group": "Projet MLOps",
            "Host": "postgres",
            "Port": 5432,
            "MaintenanceDB": os.environ["POSTGRES_DB"],
            "Username": os.environ["POSTGRES_USER"],
            "SSLMode": "prefer"
        }
    }
}

destination = Path(os.environ["PGADMIN_SERVER_JSON_FILE"])

destination.write_text(json.dumps(serveurs, indent=2, ensure_ascii=False),encoding="utf-8")

destination.chmod(0o644)

os.execv("/entrypoint.sh", ["/entrypoint.sh", *sys.argv[1:]])