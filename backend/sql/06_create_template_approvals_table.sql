-- Records each individual approval or rejection action taken by a reviewer
-- One row per action per reviewer per template
-- Also stores the unique token sent in the approval email link

CREATE TABLE IF NOT EXISTS template_approvals (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID         NOT NULL,
    reviewer_email  VARCHAR(255) NOT NULL,
    reviewer_name   VARCHAR(255),
    action          VARCHAR(10),
    comment         TEXT,
    approval_token  VARCHAR(500) NOT NULL,
    token_used      BOOLEAN      NOT NULL DEFAULT FALSE,
    token_expires_at TIMESTAMPTZ NOT NULL,
    actioned_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_template_approvals_template
        FOREIGN KEY (template_id)
        REFERENCES templates (id)
        ON DELETE CASCADE,

    -- Constraints
    CONSTRAINT uq_template_approvals_token
        UNIQUE (approval_token),

    CONSTRAINT chk_template_approvals_action
        CHECK (action IN ('approved', 'rejected') OR action IS NULL)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_template_approvals_template_id
    ON template_approvals (template_id);

CREATE INDEX IF NOT EXISTS idx_template_approvals_token
    ON template_approvals (approval_token);

CREATE INDEX IF NOT EXISTS idx_template_approvals_reviewer_email
    ON template_approvals (reviewer_email);

COMMENT ON TABLE template_approvals IS
    'Records approval and rejection actions taken by reviewers via email link';
COMMENT ON COLUMN template_approvals.approval_token IS
    '64 character cryptographically secure random token sent in approval email';
COMMENT ON COLUMN template_approvals.token_used IS
    'TRUE once the token has been actioned - prevents reuse';
COMMENT ON COLUMN template_approvals.action IS
    'NULL until reviewer acts - approved or rejected after action';
COMMENT ON COLUMN template_approvals.token_expires_at IS
    'Token expires 30 days after creation - expired tokens are rejected';