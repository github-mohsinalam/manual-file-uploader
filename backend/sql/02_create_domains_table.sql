-- Domains represent business areas (Finance, HR, Supply Chain etc.)
-- Each domain maps to a dedicated schema in Unity Catalog
-- Domains are seeded via 09_seed_domains.sql and not created via UI

CREATE TABLE IF NOT EXISTS domains (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(100) NOT NULL,
    uc_schema_name   VARCHAR(100) NOT NULL,
    description      TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    created_by       VARCHAR(255),

    -- Constraints
    CONSTRAINT uq_domains_name           UNIQUE (name),
    CONSTRAINT uq_domains_uc_schema_name UNIQUE (uc_schema_name)
);

-- Index for fast lookup by name (used in dropdowns)
CREATE INDEX IF NOT EXISTS idx_domains_name 
    ON domains (name);

COMMENT ON TABLE domains IS 
    'Business domains that map to Unity Catalog schemas';
COMMENT ON COLUMN domains.uc_schema_name IS 
    'Sanitized schema name used in Unity Catalog - lowercase, underscores only';