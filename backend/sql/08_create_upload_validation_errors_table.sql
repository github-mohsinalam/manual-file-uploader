-- Row level validation errors from Polars validation (Layer 1)
-- One row per bad cell found during validation
-- Powers the error detail table shown in the upload progress UI

CREATE TABLE IF NOT EXISTS upload_validation_errors (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    upload_id     UUID         NOT NULL,
    row_number    INTEGER      NOT NULL,
    column_name   VARCHAR(255) NOT NULL,
    error_type    VARCHAR(50)  NOT NULL,
    error_message TEXT         NOT NULL,
    raw_value     TEXT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_upload_validation_errors_upload
        FOREIGN KEY (upload_id)
        REFERENCES upload_history (id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT chk_upload_validation_errors_type
        CHECK (error_type IN (
            'NOT_NULL',
            'UNIQUE',
            'TYPE_MISMATCH',
            'SCHEMA_MISMATCH',
            'ENCODING_ERROR'
        ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_upload_validation_errors_upload_id
    ON upload_validation_errors (upload_id);

CREATE INDEX IF NOT EXISTS idx_upload_validation_errors_row_number
    ON upload_validation_errors (upload_id, row_number);

COMMENT ON TABLE upload_validation_errors IS
    'Row level validation errors from Polars Layer 1 validation';
COMMENT ON COLUMN upload_validation_errors.raw_value IS
    'The actual value from the uploaded file that caused the error';
COMMENT ON COLUMN upload_validation_errors.error_type IS
    'Category of validation failure - used for grouping in UI error report';