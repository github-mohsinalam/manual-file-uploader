-- Reviewers configured for each template approval workflow
-- Required reviewers must all approve before template goes live
-- Optional reviewers are notified but do not block approval

CREATE TABLE IF NOT EXISTS template_reviewers (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID         NOT NULL,
    reviewer_email  VARCHAR(255) NOT NULL,
    reviewer_name   VARCHAR(255),
    reviewer_type   VARCHAR(10)  NOT NULL DEFAULT 'required',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_template_reviewers_template
        FOREIGN KEY (template_id)
        REFERENCES templates (id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT uq_template_reviewers_template_email
        UNIQUE (template_id, reviewer_email),

    CONSTRAINT chk_template_reviewers_type
        CHECK (reviewer_type IN ('required', 'optional'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_reviewers_template_id
    ON template_reviewers (template_id);

CREATE INDEX IF NOT EXISTS idx_template_reviewers_email
    ON template_reviewers (reviewer_email);

COMMENT ON TABLE template_reviewers IS
    'Reviewers configured for each template - required reviewers block approval';
COMMENT ON COLUMN template_reviewers.reviewer_type IS
    'required = must approve before template goes live, optional = notified only';