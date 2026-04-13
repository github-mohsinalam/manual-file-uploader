-- Records every file upload attempt regardless of success or failure
-- This is the permanent audit trail of all uploads

CREATE TABLE IF NOT EXISTS upload_history (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id           UUID         NOT NULL,
    uploaded_by           VARCHAR(255) NOT NULL,
    uploaded_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    original_filename     VARCHAR(500) NOT NULL,
    stored_filename       VARCHAR(500),
    storage_path          VARCHAR(500),
    file_size_bytes       BIGINT,
    total_rows            INTEGER,
    valid_rows            INTEGER,
    invalid_rows          INTEGER,
    dropped_rows          INTEGER,
    status                VARCHAR(20)  NOT NULL DEFAULT 'in_progress',
    error_summary         TEXT,
    databricks_run_id     VARCHAR(100),
    dlt_rows_written      INTEGER,
    dlt_rows_dropped      INTEGER,
    dlt_event_log_path    VARCHAR(500),
    completed_at          TIMESTAMPTZ,

    -- Foreign key
    CONSTRAINT fk_upload_history_template
        FOREIGN KEY (template_id)
        REFERENCES templates (id)
        ON DELETE RESTRICT,

    -- Constraints
    CONSTRAINT chk_upload_history_status
        CHECK (status IN (
            'in_progress',
            'file_uploaded',
            'schema_validated',
            'constraints_checked',
            'writing_to_catalog',
            'completed',
            'failed',
            'partial'
        ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_upload_history_template_id
    ON upload_history (template_id);

CREATE INDEX IF NOT EXISTS idx_upload_history_uploaded_by
    ON upload_history (uploaded_by);

CREATE INDEX IF NOT EXISTS idx_upload_history_status
    ON upload_history (status);

CREATE INDEX IF NOT EXISTS idx_upload_history_uploaded_at
    ON upload_history (uploaded_at DESC);

COMMENT ON TABLE upload_history IS
    'Permanent audit trail of every file upload attempt - success or failure';
COMMENT ON COLUMN upload_history.stored_filename IS
    'Filename as stored in Blob Storage with timestamp appended';
COMMENT ON COLUMN upload_history.dlt_rows_written IS
    'Authoritative row count from DLT event log - rows actually written to UC';
COMMENT ON COLUMN upload_history.dlt_rows_dropped IS
    'Authoritative dropped row count from DLT event log';
COMMENT ON COLUMN upload_history.dlt_event_log_path IS
    'Path to DLT event log Delta table for this pipeline run';
COMMENT ON COLUMN upload_history.status IS
    'Tracks current step in the upload pipeline - drives progress stepper in UI';