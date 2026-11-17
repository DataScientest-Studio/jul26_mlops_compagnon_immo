-- À lancer dans la base de l’application.

CREATE SCHEMA IF NOT EXISTS monitoring;

-- Prédictions enregistrées par l’API pour le suivi du modèle.
CREATE TABLE IF NOT EXISTS monitoring.prediction_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    request_id UUID NOT NULL,
    model_version INTEGER NOT NULL,
    code_commune TEXT NOT NULL,
    type_local TEXT NOT NULL,
    surface_reelle_bati DOUBLE PRECISION NOT NULL,
    nombre_pieces_principales INTEGER NOT NULL,
    surface_terrain DOUBLE PRECISION,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    distance_lyon_km DOUBLE PRECISION,
    nombre_lots INTEGER,
    annee_mutation INTEGER,
    niveau_vie_median DOUBLE PRECISION,
    densite_population DOUBLE PRECISION,
    prix_m2_estime DOUBLE PRECISION NOT NULL,
    valeur_totale_estimee DOUBLE PRECISION,
    prix_total_reel NUMERIC,
    feedback_received_at TIMESTAMPTZ,
    CONSTRAINT uq_prediction_logs_request_id UNIQUE (request_id)
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_version_date
    ON monitoring.prediction_logs (model_version, created_at);

-- Chaque ligne contient une métrique calculée lors d’un run de monitoring.
CREATE TABLE IF NOT EXISTS monitoring.ml_metrics (
    id BIGSERIAL PRIMARY KEY,
    computed_at TIMESTAMPTZ NOT NULL,
    dag_run_id TEXT NOT NULL,
    model_version INTEGER NOT NULL,
    prepared_dataset_id TEXT,
    window_start TIMESTAMPTZ,
    window_end TIMESTAMPTZ,
    metric_name TEXT NOT NULL,
    column_name TEXT NOT NULL DEFAULT '',
    value DOUBLE PRECISION NOT NULL,
    CONSTRAINT uq_ml_metrics_run UNIQUE (dag_run_id, metric_name, column_name)
);

CREATE INDEX IF NOT EXISTS idx_ml_metrics_latest
    ON monitoring.ml_metrics (metric_name, column_name, computed_at DESC);
