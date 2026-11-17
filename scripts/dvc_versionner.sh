#!/usr/bin/env bash

# Uniquement des commits locaux des pointeurs ; aucun push Git.
set -euo pipefail
export DVC_NO_ANALYTICS=true
repo="$(cd "${DVC_WORKSPACE:-$(dirname "${BASH_SOURCE[0]}")/..}" && pwd -P)"
cd "$repo"

# Exception limitée à ce dépôt partagé, sans modifier la configuration globale.
n="${GIT_CONFIG_COUNT:-0}"
export "GIT_CONFIG_KEY_${n}=safe.directory" "GIT_CONFIG_VALUE_${n}=$repo"
export GIT_CONFIG_COUNT="$((n + 1))"
[[ "$(git rev-parse --show-toplevel)" == "$repo" && -d .dvc ]] || {
    echo "Initialiser DVC normalement dans le dépôt Git existant avant le DAG." >&2; exit 1;
}
[[ ! -f "$(git rev-parse --git-path MERGE_HEAD)" ]] || {
    echo "Une fusion Git est en cours." >&2; exit 1;
}
chemin="${1:?Usage: dvc_versionner.sh raw/fichier.parquet [message]}"
case "$chemin" in raw/*.parquet|prepared/*.parquet) ;; *) echo "Dataset hors périmètre." >&2; exit 1;; esac
[[ "$chemin" != *".."* && ! -L "$chemin" ]] || exit 1
case "$(realpath -m -- "$chemin")" in "$repo/raw/"*|"$repo/prepared/"*) ;; *) exit 1;; esac

# L'endpoint d'exécution ne modifie ni .dvc/config ni .dvc/config.local.
#if [[ -n "${DVC_S3_ENDPOINT:-}" ]]; then
#    export AWS_ENDPOINT_URL_S3="$DVC_S3_ENDPOINT"
#fi
remote="${DVC_REMOTE_NAME:-minio}"
dvc add -- "$chemin"
dvc push --remote "$remote" -- "$chemin.dvc"
autorises=("$chemin.dvc" "$(dirname "$chemin")/.gitignore")
git add -- "${autorises[@]}"
if ! git diff --cached --quiet -- "${autorises[@]}"; then
    git -c "user.name=${DVC_GIT_USER_NAME:-Airflow datasets}" \
        -c "user.email=${DVC_GIT_USER_EMAIL:-airflow@localhost}" \
        commit --only -m "${2:-Données : versionner $chemin}" -- "${autorises[@]}"
fi
