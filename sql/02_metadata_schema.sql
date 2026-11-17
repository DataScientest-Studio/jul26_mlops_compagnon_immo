-- Garde le lien entre les données DVC, les tables chargées et les modèles MLflow.
-- L’identifiant d’un dataset est l’empreinte MD5 calculée par DVC.

CREATE SCHEMA IF NOT EXISTS metadata;

-- Versions des données brutes DVF et INSEE.
CREATE TABLE IF NOT EXISTS metadata.raw_datasets (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('dvf', 'insee')),
    collected_at TIMESTAMPTZ NOT NULL, -- Première collecte de ce contenu.
    last_seen_at TIMESTAMPTZ NOT NULL, -- Dernière collecte du même contenu.
    source_url TEXT,
    nb_lignes BIGINT NOT NULL,
    taille_octets BIGINT,
    chemin_dvc TEXT NOT NULL,
    uri_minio TEXT NOT NULL,
    fichier_dvc TEXT NOT NULL,
    dag_run_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_datasets_source
    ON metadata.raw_datasets (source, collected_at DESC);

-- Données préparées et versions des deux sources utilisées.
CREATE TABLE IF NOT EXISTS metadata.prepared_datasets (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL,
    nb_lignes BIGINT NOT NULL,
    taille_octets BIGINT,
    chemin_dvc TEXT NOT NULL,
    uri_minio TEXT NOT NULL,
    fichier_dvc TEXT NOT NULL,
    raw_dvf_id TEXT NOT NULL REFERENCES metadata.raw_datasets (id),
    raw_insee_id TEXT NOT NULL REFERENCES metadata.raw_datasets (id),
    git_commit TEXT, -- Version du code de préparation.
    dag_run_id TEXT
);

-- Dataset préparé actuellement chargé dans chaque table.
CREATE TABLE IF NOT EXISTS metadata.loaded_tables (
    table_name TEXT PRIMARY KEY,
    prepared_dataset_id TEXT NOT NULL REFERENCES metadata.prepared_datasets (id),
    loaded_at TIMESTAMPTZ NOT NULL,
    nb_lignes BIGINT NOT NULL
);

-- Versions des modèles et résultats de leur entraînement.
CREATE TABLE IF NOT EXISTS metadata.model_versions (
    model_version INTEGER PRIMARY KEY,
    run_id TEXT NOT NULL,
    prepared_dataset_id TEXT REFERENCES metadata.prepared_datasets (id),
    trained_at TIMESTAMPTZ NOT NULL,
    nb_lignes BIGINT,
    mae DOUBLE PRECISION,
    rmse DOUBLE PRECISION,
    r2 DOUBLE PRECISION,
    mae_cv DOUBLE PRECISION,
    decision TEXT,
    est_champion BOOLEAN NOT NULL DEFAULT FALSE,
    promu_at TIMESTAMPTZ
);

-- Empêche de marquer deux modèles comme champions en même temps.
CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_champion
    ON metadata.model_versions (est_champion)
    WHERE est_champion;

-- Retrouve les données préparées et les sources utilisées pour chaque modèle.
CREATE OR REPLACE VIEW metadata.lignage AS
SELECT
    m.model_version,
    m.est_champion,
    m.mae,
    m.run_id,
    p.id AS prepared_dataset_id,
    p.created_at AS prepare_le,
    p.uri_minio AS uri_prepare,
    d.id AS raw_dvf_id,
    d.collected_at AS dvf_collecte_le,
    d.uri_minio AS uri_dvf,
    i.id AS raw_insee_id,
    i.collected_at AS insee_collecte_le,
    i.uri_minio AS uri_insee
FROM metadata.model_versions m
LEFT JOIN metadata.prepared_datasets p
    ON p.id = m.prepared_dataset_id
LEFT JOIN metadata.raw_datasets d
    ON d.id = p.raw_dvf_id
LEFT JOIN metadata.raw_datasets i
    ON i.id = p.raw_insee_id;
