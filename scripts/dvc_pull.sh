#!/usr/bin/env bash
# Le pointeur à utiliser doit déjà avoir été sélectionné avec Git.
set -euo pipefail
export DVC_NO_ANALYTICS=true
repo="$(cd "${DVC_WORKSPACE:-$(dirname "${BASH_SOURCE[0]}")/..}" && pwd -P)"
cd "$repo"
n="${GIT_CONFIG_COUNT:-0}"
export "GIT_CONFIG_KEY_${n}=safe.directory" "GIT_CONFIG_VALUE_${n}=$repo"
export GIT_CONFIG_COUNT="$((n + 1))"
[[ "$(git rev-parse --show-toplevel)" == "$repo" && -d .dvc ]] || exit 1
chemin="${1:?Usage: dvc_pull.sh raw/fichier.parquet}"
case "$chemin" in raw/*.parquet|prepared/*.parquet) ;; *) echo "Dataset hors périmètre." >&2; exit 1;; esac
[[ "$chemin" != *".."* && ! -L "$chemin" ]] || exit 1
case "$(realpath -m -- "$chemin")" in "$repo/raw/"*|"$repo/prepared/"*) ;; *) exit 1;; esac
#if [[ -n "${DVC_S3_ENDPOINT:-}" ]]; then
#    export AWS_ENDPOINT_URL_S3="$DVC_S3_ENDPOINT"
#fi
dvc pull --remote "${DVC_REMOTE_NAME:-minio}" -- "$chemin.dvc"
