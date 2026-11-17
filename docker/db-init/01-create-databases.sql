-- Crée les bases de MLflow et d'Airflow si elles n'existent pas encore.
-- La base de l'application, définie par POSTGRES_DB, est créée par PostgreSQL
-- lors de l'initialisation de son dossier de données.
SELECT 'CREATE DATABASE mlflow_metadata'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow_metadata')\gexec
SELECT 'CREATE DATABASE airflow_metadata'
 WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow_metadata')\gexec
