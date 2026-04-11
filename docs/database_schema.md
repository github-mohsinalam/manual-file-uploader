**domains**   
<paragraph>*This stores the list of business domains — Finance, HR, Supply Chain etc. Each domain maps to a schema in Unity Catalog.*</paragraph>  

├── id               UUID, PRIMARY KEY  
├── name             VARCHAR(100), NOT NULL, UNIQUE   -- e.g. "Finance"  
├── uc_schema_name   VARCHAR(100), NOT NULL, UNIQUE   -- e.g. "finance"  
├── description      TEXT  
├── created_at       TIMESTAMP, DEFAULT NOW()  
└── created_by       VARCHAR(255)  

**templates**  
<paragraph>*Table to store one row per template created by a user.*</paragraph>  

├── id                    UUID, PRIMARY KEY  
├── name                  VARCHAR(255), NOT NULL  
├── display_name          VARCHAR(255), NOT NULL  
├── description           TEXT  
├── domain_id             UUID, FOREIGN KEY → domains.id  
├── uc_table_name         VARCHAR(255), NOT NULL  -- auto generated  
├── fully_qualified_name  VARCHAR(500), NOT NULL  -- catalog.schema.table  
├── file_format           VARCHAR(10)             -- csv, xlsx  
├── delimiter             VARCHAR(5)              -- comma, pipe, tab  
├── encoding              VARCHAR(20)             -- UTF-8 etc  
├── write_mode            VARCHAR(10)             -- append, overwrite  
├── bad_row_threshold     DECIMAL(5,2)            -- e.g. 5.00 for 5%  
├── bad_row_action        VARCHAR(10)             -- fail, drop  
├── storage_path          VARCHAR(500)            -- Blob Storage path  
├── reader_group          VARCHAR(255)            -- AD group name  
├── status                VARCHAR(50)             -- Draft, Pending, Approved, Rejected, Deprecated  
├── version               INTEGER, DEFAULT 1  
├── parent_template_id    UUID, FOREIGN KEY → templates.id  -- for versioning  
├── created_by            VARCHAR(255)  
├── created_at            TIMESTAMP, DEFAULT NOW()  
├── updated_at            TIMESTAMP, DEFAULT NOW()  
└── approved_at           TIMESTAMP  

`fully_qualified_name` is stored as a convenience — it is always `manualuploads.{uc_schema_name}.{uc_table_name}` but storing it avoids recomputing it every time.  
`parent_template_id` is self-referencing — when a user edits an approved template it creates a new version row that points back to the original template via this column.  


**template_columns**  
<paragraph>*Each template has multiple columns. This table stores the configuration for each column.*</paragraph>  

├── id               UUID, PRIMARY KEY  
├── template_id      UUID, FOREIGN KEY → templates.id  
├── column_name      VARCHAR(255), NOT NULL  
├── display_name     VARCHAR(255)  
├── data_type        VARCHAR(50)    -- STRING, INTEGER, DATE, TIMESTAMP etc  
├── description      TEXT           -- user provided column description  
├── is_included      BOOLEAN        -- did user choose to include this column  
├── is_pii           BOOLEAN        -- is this a PII column  
├── is_nullable      BOOLEAN        -- NOT NULL constraint  
├── is_unique        BOOLEAN        -- UNIQUE constraint  
├── column_order     INTEGER        -- display order  
└── created_at       TIMESTAMP, DEFAULT NOW()  

**template_reviewers**  
<paragraph>*Stores who needs to review and approve each template.*</paragraph>  

├── id               UUID, PRIMARY KEY  
├── template_id      UUID, FOREIGN KEY → templates.id  
├── reviewer_email   VARCHAR(255), NOT NULL  
├── reviewer_name    VARCHAR(255)  
├── reviewer_type    VARCHAR(10)    -- required, optional  
└── created_at       TIMESTAMP, DEFAULT NOW()  

**template_approvals**  
<paragraph>*Tracks each individual approval action taken by a reviewer.*</paragraph>  

├── id               UUID, PRIMARY KEY  
├── template_id      UUID, FOREIGN KEY → templates.id  
├── reviewer_email   VARCHAR(255), NOT NULL  
├── action           VARCHAR(10)    -- approved, rejected  
├── comment          TEXT           -- rejection reason or approval note  
├── actioned_at      TIMESTAMP, DEFAULT NOW()  
└── approval_token   VARCHAR(500)   -- unique token sent in email link  

`approval_token` is important for security. When we send the approval email the link contains a unique token — something like `https://yourapp.com/approve?token=abc123xyz`. The backend validates this token before recording the approval. This prevents anyone from approving a template just by guessing the URL.

**upload_history**  
<paragraph>*Every file upload attempt gets recorded here — success or failure.*</paragraph>  

├── id                    UUID, PRIMARY KEY  
├── template_id           UUID, FOREIGN KEY → templates.id  
├── uploaded_by           VARCHAR(255)  
├── uploaded_at           TIMESTAMP, DEFAULT NOW()  
├── original_filename     VARCHAR(500)  
├── stored_filename       VARCHAR(500)   -- filename with timestamp appended  
├── storage_path          VARCHAR(500)   -- full Blob Storage path  
├── file_size_bytes       BIGINT  
├── total_rows            INTEGER  
├── valid_rows            INTEGER  
├── invalid_rows          INTEGER  
├── status                VARCHAR(20)    -- success, failed, partial  
├── error_summary         TEXT           -- high level error description  
├── databricks_run_id     VARCHAR(100)   -- run_id from Databricks job  
└── completed_at          TIMESTAMP  

`databricks_run_id` is the job run ID returned by the Databricks REST API. We store it so we can poll job status and also for debugging if something goes wrong.

**upload_validation_errors**  
<paragraph>*Row level validation errors for each upload. This powers the error table in the UI stepper.*</paragraph>  

├── id               UUID, PRIMARY KEY  
├── upload_id        UUID, FOREIGN KEY → upload_history.id  
├── row_number       INTEGER  
├── column_name      VARCHAR(255)  
├── error_type       VARCHAR(50)    -- NOT_NULL, UNIQUE, TYPE_MISMATCH etc  
├── error_message    TEXT  
└── raw_value        TEXT           -- the actual bad value from the file  

**How these tables relate to each other**  
domains (1) ──────────────── (many) templates  
templates (1) ─────────────── (many) template_columns  
templates (1) ─────────────── (many) template_reviewers  
templates (1) ─────────────── (many) template_approvals  
templates (1) ─────────────── (many) upload_history  
upload_history (1) ──────────── (many) upload_validation_errors  
templates (1) ──── self ──────── (many) templates  [versioning]  