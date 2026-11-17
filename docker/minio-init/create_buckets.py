"""Crée les buckets MinIO manquants. Utilise boto3, déjà présent dans l'image MLflow."""
import os
import sys
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BUCKETS = os.getenv("MINIO_BUCKETS", "mlflow-artifacts,dvc-data").split(",")

s3 = boto3.client("s3", endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"])

for tentative in range(1, 31):                     
    try:
        existants = {b["Name"] for b in s3.list_buckets()["Buckets"]}
        break
    except (BotoCoreError, ClientError) as erreur:
        print(f"MinIO indisponible ({tentative}/30) : {erreur}", flush=True)
        time.sleep(2)
else:
    sys.exit("MinIO injoignable")

for bucket in BUCKETS:
    if bucket in existants:
        print(f"Bucket '{bucket}' déjà présent")
    else:
        s3.create_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' créé")
