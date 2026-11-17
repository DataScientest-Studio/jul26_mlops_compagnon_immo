-- Facilite la recherche des dernières métriques pour chaque version du modèle.
-- Les index déjà présents sont conservés.
CREATE INDEX IF NOT EXISTS idx_ml_metrics_latest_version
    ON monitoring.ml_metrics (
        metric_name,
        column_name,
        model_version,
        computed_at DESC,
        id DESC
    );
