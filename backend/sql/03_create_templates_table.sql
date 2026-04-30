-- Templates define the structure and configuration of a manual mapping file
-- One template = one Unity Catalog table
-- Templates go through a lifecycle: Draft → Pending Approval → Approved → Deprecated

CREATE TABLE IF NOT EXISTS templates (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(255) NOT NULL,
    display_name          VARCHAR(255) NOT NULL,
    description           TEXT,
    domain_id             UUID         NOT NULL,
    uc_table_name         VARCHAR(255) NOT NULL,
    fully_qualified_name  VARCHAR(500) NOT NULL,
    file_format           VARCHAR(10)  NOT NULL DEFAULT 'csv',
    delimiter             VARCHAR(5)   NOT NULL DEFAULT ',',
    encoding              VARCHAR(20)  NOT NULL DEFAULT 'UTF-8',
    write_mode            VARCHAR(10)  NOT NULL DEFAULT 'append',
    bad_row_threshold     DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    bad_row_action        VARCHAR(10)  NOT NULL DEFAULT 'fail',
    storage_path          VARCHAR(500),
    reader_group          VARCHAR(255),
    status                VARCHAR(50)  NOT NULL DEFAULT 'Draft',
    version               INTEGER      NOT NULL DEFAULT 1,
    parent_template_id    UUID,
    created_by            VARCHAR(255) NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    approved_at           TIMESTAMPTZ,
    databricks_ddl_run_id VARCHAR(100),

    -- Foreign keys
    CONSTRAINT fk_templates_domain
        FOREIGN KEY (domain_id)
        REFERENCES domains (id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_templates_parent
        FOREIGN KEY (parent_template_id)
        REFERENCES templates (id)
        ON DELETE RESTRICT,

    -- Constraints
    CONSTRAINT uq_templates_fully_qualified_name
        UNIQUE (fully_qualified_name),

    CONSTRAINT chk_templates_file_format
        CHECK (file_format IN ('csv', 'xlsx')),

    CONSTRAINT chk_templates_write_mode
        CHECK (write_mode IN ('append', 'overwrite')),

    CONSTRAINT chk_templates_bad_row_action
        CHECK (bad_row_action IN ('fail', 'drop')),

    CONSTRAINT chk_templates_status
        CHECK (status IN (
            'Draft',
            'Pending Approval',
            'Pending DDL',
            'Approved',
            'Rejected',
            'DDL Failed',
            'Deprecated'
        )),

    CONSTRAINT chk_templates_bad_row_threshold
        CHECK (bad_row_threshold >= 0 AND bad_row_threshold <= 100),

    CONSTRAINT chk_templates_version
        CHECK (version >= 1)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_templates_domain_id
    ON templates (domain_id);

CREATE INDEX IF NOT EXISTS idx_templates_status
    ON templates (status);

CREATE INDEX IF NOT EXISTS idx_templates_created_by
    ON templates (created_by);

CREATE INDEX IF NOT EXISTS idx_templates_parent_template_id
    ON templates (parent_template_id);

COMMENT ON TABLE templates IS
    'Template definitions for manual mapping files and their UC table configuration';
COMMENT ON COLUMN templates.fully_qualified_name IS
    'Auto generated - format: manualuploads.{schema}.{table}';
COMMENT ON COLUMN templates.parent_template_id IS
    'Points to original template when this row is a new version';
COMMENT ON COLUMN templates.databricks_ddl_run_id IS
    'run_id returned by Databricks REST API when DDL job is triggered';
COMMENT ON COLUMN templates.bad_row_threshold IS
    'Percentage of bad rows acceptable before upload is rejected - 0 to 100';