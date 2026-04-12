-- Column level configuration for each template
-- One row per column that the user configured during template creation

CREATE TABLE IF NOT EXISTS template_columns (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id   UUID         NOT NULL,
    column_name   VARCHAR(255) NOT NULL,
    display_name  VARCHAR(255),
    data_type     VARCHAR(50)  NOT NULL DEFAULT 'STRING',
    description   TEXT,
    is_included   BOOLEAN      NOT NULL DEFAULT TRUE,
    is_pii        BOOLEAN      NOT NULL DEFAULT FALSE,
    is_nullable   BOOLEAN      NOT NULL DEFAULT TRUE,
    is_unique     BOOLEAN      NOT NULL DEFAULT FALSE,
    column_order  INTEGER      NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_template_columns_template
        FOREIGN KEY (template_id)
        REFERENCES templates (id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT uq_template_columns_template_column
        UNIQUE (template_id, column_name),

    CONSTRAINT chk_template_columns_data_type
        CHECK (data_type IN (
            'STRING',
            'INTEGER',
            'LONG',
            'DOUBLE',
            'DECIMAL',
            'BOOLEAN',
            'DATE',
            'TIMESTAMP'
        ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_columns_template_id
    ON template_columns (template_id);

CREATE INDEX IF NOT EXISTS idx_template_columns_is_included
    ON template_columns (template_id, is_included);

COMMENT ON TABLE template_columns IS
    'Column level configuration for each template including types, PII flags and constraints';
COMMENT ON COLUMN template_columns.is_nullable IS
    'FALSE means NOT NULL constraint applied - column must have a value';
COMMENT ON COLUMN template_columns.is_unique IS
    'Informational in Delta Lake - enforced exclusively by Polars validation layer';
COMMENT ON COLUMN template_columns.description IS
    'User provided description - applied as COMMENT on the UC table column';