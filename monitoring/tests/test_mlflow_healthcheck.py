"""Teste la sonde sans écrire dans PostgreSQL ni dans S3."""
import importlib.util
import io
import os
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import MagicMock, patch
from urllib.error import URLError

path = Path(__file__).resolve().parents[2] / "docker/mlflow/healthcheck.py"
spec = importlib.util.spec_from_file_location("healthcheck", path)
healthcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(healthcheck)


class HealthcheckTest(TestCase):
    @patch.dict(os.environ, {"MLFLOW_S3_ENDPOINT_URL": "http://minio:9000"})
    @patch.object(healthcheck.boto3, "client")
    @patch.object(healthcheck, "urlopen")
    def test_http_database_bucket(self, urlopen, boto):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        database_response = io.BytesIO(b'{"experiments":[]}')
        urlopen.side_effect = [response, database_response]
        healthcheck.verifier()
        self.assertIn("/experiments/search", urlopen.call_args_list[1].args[0].full_url)
        boto.return_value.head_bucket.assert_called_once_with(Bucket="mlflow-artifacts")
        boto.return_value.put_object.assert_not_called()

    @patch.object(healthcheck, "urlopen", side_effect=URLError("indisponible"))
    def test_http_failure(self, _):
        with self.assertRaises(URLError):
            healthcheck.verifier()

    @patch.dict(os.environ, {"MLFLOW_S3_ENDPOINT_URL": "http://minio:9000"})
    @patch.object(healthcheck.boto3, "client")
    @patch.object(healthcheck, "urlopen")
    def test_bucket_failure(self, urlopen, boto):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        urlopen.side_effect = [response, io.BytesIO(b'{"experiments":[]}')]
        boto.return_value.head_bucket.side_effect = RuntimeError("bucket indisponible")
        with self.assertRaisesRegex(RuntimeError, "bucket indisponible"):
            healthcheck.verifier()


if __name__ == "__main__":
    main(verbosity=2)
