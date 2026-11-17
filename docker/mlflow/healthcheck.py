"""Disponibilité MLflow : HTTP + accès lecture au backend SQL et au bucket.

"""
import json
import os
from urllib.request import Request, urlopen

import boto3
from botocore.config import Config


def verifier():
    with urlopen("http://localhost:5000/health", timeout=3) as response:
        if response.status != 200:
            raise RuntimeError("MLflow HTTP indisponible")
    request = Request(
        "http://localhost:5000/api/2.0/mlflow/experiments/search",
        data=json.dumps({"max_results": 1}).encode(),
        headers={"Content-Type": "application/json"},
    )

    with urlopen(request, timeout=4) as response:
        json.load(response)  # Requête SQL de lecture, pas seulement /health.
    boto3.client(
        "s3",
        endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"],
        config=Config(connect_timeout=2, read_timeout=2, retries={"total_max_attempts": 1}),
    ).head_bucket(Bucket="mlflow-artifacts")


if __name__ == "__main__":
    verifier()
