-- Les anciennes valeurs de fichier_dvc restent en base.
-- Les nouveaux enregistrements peuvent laisser cette colonne vide.
ALTER TABLE metadata.raw_datasets
    ALTER COLUMN fichier_dvc DROP NOT NULL;

ALTER TABLE metadata.prepared_datasets
    ALTER COLUMN fichier_dvc DROP NOT NULL;

-- Ajoute le commit des pointeurs DVC et les informations du fichier Parquet.
ALTER TABLE metadata.raw_datasets
    ADD COLUMN IF NOT EXISTS dvc_git_commit TEXT,
    ADD COLUMN IF NOT EXISTS metadonnees JSONB;

ALTER TABLE metadata.prepared_datasets
    ADD COLUMN IF NOT EXISTS dvc_git_commit TEXT,
    ADD COLUMN IF NOT EXISTS metadonnees JSONB;

-- Ces descriptions sont enregistrées dans PostgreSQL.
COMMENT ON COLUMN metadata.raw_datasets.fichier_dvc IS
    'Historique avant Git/DVC natif uniquement ; plus alimenté.';

COMMENT ON COLUMN metadata.prepared_datasets.fichier_dvc IS
    'Historique avant Git/DVC natif uniquement ; plus alimenté.';

COMMENT ON COLUMN metadata.prepared_datasets.git_commit IS
    'Version du code de préparation ; distincte de dvc_git_commit.';
