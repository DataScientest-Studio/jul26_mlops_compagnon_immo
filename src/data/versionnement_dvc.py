"""DVC natif et Git dans le dépôt existant ; métadonnées descriptives Parquet."""

import json
import logging
import os
import re
import subprocess
from pathlib import Path

import dvc.api
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

log = logging.getLogger(__name__)
CLE_METADATA = b"compagnon_immobilier"


def dossier_depot() -> Path:
    return Path(os.getenv("DVC_WORKSPACE", Path(__file__).resolve().parents[2])).resolve()


def _env() -> dict:
    env = {**os.environ, "DVC_NO_ANALYTICS": "true"}
    n = int(env.get("GIT_CONFIG_COUNT", "0"))
    env.update({f"GIT_CONFIG_KEY_{n}": "safe.directory",
                f"GIT_CONFIG_VALUE_{n}": str(dossier_depot()),
                "GIT_CONFIG_COUNT": str(n + 1)})
    return env


def _commande(*args: str) -> str:
    res = subprocess.run(args, cwd=dossier_depot(), env=_env(),
                         capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(f"Commande {args[0]} échouée ({res.returncode}) :\n"
                           f"{res.stdout}\n{res.stderr}")
    log.info("%s", res.stdout.strip())
    return res.stdout.strip()


def initialiser_depot() -> Path:
    """Vérifie l'initialisation ; ne crée ni dépôt, ni clone, ni branche."""
    depot = dossier_depot()
    racine = Path(_commande("git", "rev-parse", "--show-toplevel")).resolve()
    if racine != depot or not (depot / ".dvc").is_dir():
        raise RuntimeError("DVC_WORKSPACE doit être la racine Git avec DVC initialisé.")
    return depot


def _chemin(chemin_relatif: str) -> Path:
    relatif = Path(chemin_relatif)
    depot = dossier_depot()
    cible = depot / relatif
    if (relatif.is_absolute() or ".." in relatif.parts or
            len(relatif.parts) < 2 or relatif.parts[0] not in ("raw", "prepared") or
            relatif.suffix != ".parquet" or cible.is_symlink() or
            not cible.resolve().is_relative_to((depot / relatif.parts[0]).resolve()) or
            not cible.resolve().is_relative_to(depot)):
        raise ValueError(f"Dataset hors périmètre : {chemin_relatif}")
    return cible


def ecrire_parquet(df: pd.DataFrame, chemin_relatif: str, metadonnees: dict) -> Path:
    """Métadonnées dans le schéma, avant dvc add, sans colonnes métier ajoutées."""
    initialiser_depot()
    cible = _chemin(chemin_relatif)
    cible.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, preserve_index=False)
    schema_metadata = dict(table.schema.metadata or {})
    schema_metadata[CLE_METADATA] = json.dumps(
        metadonnees, ensure_ascii=False, sort_keys=True).encode("utf-8")
    table = table.replace_schema_metadata(schema_metadata)
    # Ne jamais modifier en place un fichier éventuellement lié au cache DVC.
    temporaire = cible.with_suffix(".parquet.tmp")
    try:
        pq.write_table(table, temporaire)
        temporaire.replace(cible)
    finally:
        temporaire.unlink(missing_ok=True)
    return cible


def lire_metadonnees(chemin_relatif: str) -> dict:
    metadata = pq.read_schema(_chemin(chemin_relatif)).metadata or {}
    return json.loads(metadata[CLE_METADATA].decode("utf-8"))


def lire_parquet(chemin_relatif: str) -> pd.DataFrame:
    initialiser_depot()
    _chemin(chemin_relatif)
    _commande("bash", str(dossier_depot() / "scripts/dvc_pull.sh"), chemin_relatif)
    return pd.read_parquet(_chemin(chemin_relatif))


def versionner_fichier(chemin_relatif: str) -> dict:
    """Les scripts gèrent add/push/commit ; seul DVC calcule le hash."""
    depot = initialiser_depot()
    fichier = _chemin(chemin_relatif)
    if not fichier.is_file():
        raise FileNotFoundError(fichier)
    _commande("bash", str(depot / "scripts/dvc_versionner.sh"), chemin_relatif)
    pointeur = Path(str(fichier) + ".dvc")
    sortie = yaml.safe_load(pointeur.read_text(encoding="utf-8"))["outs"][0]
    md5 = sortie["md5"]
    if sortie.get("hash", "md5") != "md5" or not re.fullmatch(r"[0-9a-f]{32}", md5):
        raise RuntimeError(f"Empreinte DVC inattendue dans {pointeur}")
    commit = _commande("git", "rev-parse", "HEAD")
    # DVC résout lui-même la disposition physique des objets du remote.
    uri = dvc.api.get_url(chemin_relatif, repo=str(depot), rev=commit,
                          remote=os.getenv("DVC_REMOTE_NAME", "minio"))
    return {"id": md5, "chemin_dvc": chemin_relatif,
            "taille_octets": int(sortie.get("size", fichier.stat().st_size)),
            "uri_minio": uri, "dvc_git_commit": commit,
            "metadonnees": lire_metadonnees(chemin_relatif)}


def restaurer(revision_git: str, chemin_dvc: str) -> Path:
    """Sélection explicite d'un ancien pointeur puis pull, dans le même dépôt.

    Maintenance uniquement, DAG suspendu. HEAD et l'index restent inchangés.
    Refuse d'écraser un pointeur ou un dataset modifié. Aucune reconstruction YAML.
    """
    depot = initialiser_depot()
    fichier = _chemin(chemin_dvc)
    pointeur = chemin_dvc + ".dvc"
    revision = _commande("git", "rev-parse", "--verify", f"{revision_git}^{{commit}}")
    if _commande("git", "status", "--porcelain", "--", pointeur):
        raise RuntimeError("Pointeur modifié : sauvegarder avant la restauration.")
    actuel = json.loads(_commande("dvc", "status", "--json", pointeur))
    if actuel and fichier.exists():
        raise RuntimeError("Dataset modifié : sauvegarder avant la restauration.")
    _commande("git", "restore", f"--source={revision}", "--worktree", "--", pointeur)
    try:
        _commande("bash", str(depot / "scripts/dvc_pull.sh"), chemin_dvc)
    except Exception:
        _commande("git", "restore", "--worktree", "--", pointeur)
        raise
    return fichier


def lire_version(revision_git: str, chemin_dvc: str) -> pd.DataFrame:
    """Lecture historique volontaire ; reste sur le pointeur sélectionné."""
    return pd.read_parquet(restaurer(revision_git, chemin_dvc))
