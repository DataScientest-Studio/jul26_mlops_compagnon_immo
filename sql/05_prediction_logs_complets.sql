-- Complète le journal d’une base existante sans supprimer les anciennes lignes.
-- Les nouvelles colonnes ne sont pas remplies pour les anciennes prédictions.

BEGIN;

-- Bloque les écritures concurrentes pendant les contrôles et la mise à jour.
LOCK TABLE monitoring.prediction_logs IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
    nb_sans_id BIGINT;
BEGIN
    -- Arrête la migration si plusieurs lignes ont le même identifiant.
    IF EXISTS (
        SELECT request_id
        FROM monitoring.prediction_logs
        WHERE request_id IS NOT NULL
        GROUP BY request_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'Request ID dupliqués : migration annulée, examiner les lignes sans les supprimer';
    END IF;

    -- Garde les anciennes lignes qui n’ont pas d’identifiant.
    SELECT COUNT(*) INTO nb_sans_id
    FROM monitoring.prediction_logs
    WHERE request_id IS NULL;

    IF nb_sans_id > 0 THEN
        RAISE NOTICE '% anciennes lignes sans Request ID conservées ; retour impossible pour ces lignes', nb_sans_id;
    ELSE
        -- Rend l’identifiant obligatoire si toutes les lignes en ont déjà un.
        ALTER TABLE monitoring.prediction_logs ALTER COLUMN request_id SET NOT NULL;
    END IF;
END $$;

-- Ajoute les caractéristiques du logement et le retour du prix réel.
ALTER TABLE monitoring.prediction_logs
    ADD COLUMN IF NOT EXISTS surface_terrain DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS distance_lyon_km DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS nombre_lots INTEGER,
    ADD COLUMN IF NOT EXISTS annee_mutation INTEGER,
    ADD COLUMN IF NOT EXISTS niveau_vie_median DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS densite_population DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS valeur_totale_estimee DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS prix_total_reel NUMERIC,
    ADD COLUMN IF NOT EXISTS feedback_received_at TIMESTAMPTZ;

-- La surface du terrain peut rester inconnue.
ALTER TABLE monitoring.prediction_logs
    ALTER COLUMN surface_terrain DROP NOT NULL;

-- Autorise plusieurs identifiants NULL, mais pas deux identifiants identiques.
CREATE UNIQUE INDEX IF NOT EXISTS uq_prediction_logs_request_id
    ON monitoring.prediction_logs (request_id);

COMMIT;
