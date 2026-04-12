# Manual File Uploader — Implementation Decisions

This document locks the technical implementation approach for every
feature before development begins. It exists to prevent back-and-forth
during development and serves as the authoritative reference for how
each feature is built.

---

## 1. Domain Management

### Decision
Domains are seeded into the PostgreSQL database as static reference
data via a SQL seed script. They are not created dynamically through
the UI in the first version.

### Rationale
Domains map directly to Unity Catalog schemas which require deliberate
governance decisions. A fixed seed list prevents accidental schema
proliferation in the catalog.

### Implementation
- domains table in PostgreSQL holds all valid domains
- A seed SQL script populates initial domains on first setup
- FastAPI exposes a GET /domains endpoint that reads from PostgreSQL
- React dropdown reads from this endpoint

---

## 2. Template Management

### 2.1 Template Creation

#### Decision
Template creation is a multi-step wizard in the UI. The backend saves
the template progressively — a Draft record is created first, then
updated as each wizard step is completed. The template is not submitted
for approval until the user explicitly clicks Submit.

#### Implementation
- POST /templates — creates Draft record in PostgreSQL
- PATCH /templates/{id} — updates template as wizard steps complete
- POST /templates/{id}/columns — saves column configurations
- POST /templates/{id}/reviewers — saves reviewer list
- POST /templates/{id}/submit — triggers approval workflow
- Sample file parsed in FastAPI using Pandas — column names and
  inferred data types extracted and returned to UI
- Fully qualified name generated server side —
  manualuploads.{uc_schema_name}.{sanitized_template_name}
- Name uniqueness checked against both PostgreSQL templates table
  AND Unity Catalog via Databricks REST API to confirm no table
  exists with that name

### 2.2 Template Versioning

#### Decision
Editing an approved template creates a new row in the templates table
with an incremented version number and a parent_template_id pointing
to the original. The original template row is never modified.

#### Implementation
- POST /templates/{id}/new-version — clones the approved template
  into a new Draft row with version + 1
- Original template remains Approved and Active and continues to
  accept uploads until the new version is approved
- On new version approval the original is set to Deprecated
  automatically

### 2.3 Template Status Lifecycle

#### Decision
Status transitions are strictly controlled server side. The UI cannot
directly set a status — it can only call specific action endpoints
that trigger valid transitions.

#### Valid transitions
- Draft → Pending Approval (via submit action)
- Pending Approval → Approved (via approval completion check)
- Pending Approval → Rejected (via rejection action)
- Approved → Deprecated (via new version approval)

#### Implementation
- Status stored as VARCHAR in PostgreSQL templates table
- Each transition has a dedicated FastAPI endpoint
- Invalid transitions return HTTP 400 with clear error message

---

## 3. Approval Workflow

### 3.1 Approval Email

#### Decision
Azure Communication Services Email used for sending approval
notifications. Emails are triggered by FastAPI directly — no
separate job or queue needed for email sending since emails are
fast and do not require Databricks compute.

#### Implementation
- On POST /templates/{id}/submit FastAPI sends emails to all
  reviewers synchronously using Azure Communication Services SDK
- Each reviewer gets a unique approval token generated server side
  using Python secrets module (cryptographically secure random string)
- Token stored in template_approvals table with reviewer email
  and template id
- Approval link format:
  https://{app_url}/approve?token={unique_token}
- Reminder emails triggered by a scheduled Databricks job that
  runs daily — checks for templates in Pending Approval status
  older than the configured reminder threshold and sends reminder
  emails to pending required reviewers

### 3.2 Approval Recording

#### Decision
Approval actions are unauthenticated token-based — the reviewer
clicks the link in their email which contains the token. No login
required to approve. This is intentional — requiring login creates
friction and reduces approval completion rate.

#### Security
- Token is a 64 character cryptographically secure random string
- One token per reviewer per template — cannot approve for
  someone else
- Token is single use — once actioned it cannot be used again
- Token expiry — tokens expire after 30 days

#### Implementation
- GET /approve?token={token} — FastAPI validates token, returns
  template details for the approval UI page
- POST /approve — FastAPI records approval or rejection action,
  marks token as used, triggers completion check
- After every approval action FastAPI checks if all required
  reviewers have approved — if yes triggers DDL job

### 3.3 Completion Check

#### Decision
After every approval action FastAPI queries the template_approvals
table to count how many required reviewers have approved. If count
equals the total required reviewer count the DDL job is triggered.

#### Implementation
- Pure SQL query — count approved actions for required reviewers
  on this template
- If complete: POST to Databricks REST API to trigger DDL job,
  update template status to Pending DDL
- If any rejection exists: update template status to Rejected,
  send rejection notification email to creator

---

## 4. Unity Catalog Table Provisioning

### 4.1 DDL Job

#### Decision
Non-declarative PySpark script (not DLT) used for the DDL job.
DLT is not appropriate here because the DDL job only runs once per
template approval and does not involve data ingestion. DLT pipelines
are designed for ongoing streaming or batch data flows not one-time
schema provisioning.

#### Implementation
- Databricks notebook stored in the databricks/ folder in the repo
  and uploaded to Databricks workspace during setup
- FastAPI triggers the notebook via Databricks Jobs REST API
  (POST /api/2.1/jobs/runs/submit)
- Notebook receives template_id as a parameter
- Notebook reads full template definition from PostgreSQL
- Notebook dynamically builds and executes CREATE TABLE statement
  using Spark SQL
- Column comments applied via ALTER TABLE ALTER COLUMN SET COMMENT
- PII masking applied via CREATE ROW FILTER / COLUMN MASK in UC
- NOT NULL enforced via ALTER TABLE ADD CONSTRAINT CHECK
  (column IS NOT NULL)
- UNIQUE constraint added as informational metadata only —
  NOT enforced by Delta Lake. Actual uniqueness enforced in
  FastAPI validation layer at upload time (see section 5.3)
- UC grants applied via GRANT SQL statements in the notebook
  (USE CATALOG, USE SCHEMA, SELECT)
- FastAPI polls job status via GET /api/2.1/jobs/runs/get
  using the run_id returned from job submission
- On job success FastAPI updates template status to
  Approved and Active in PostgreSQL
- On job failure FastAPI updates template status back to
  Pending Approval and notifies creator

---

## 5. File Upload

### 5.1 Upload Flow

#### Implementation
- GET /templates/approved — returns only Active templates for
  the upload dropdown, filtered by domain selection
- POST /uploads — multipart form endpoint receives domain,
  template_id and file bytes

### 5.2 File Storage

#### Decision
Raw file written to Azure Blob Storage immediately on receipt
before any validation runs. This ensures every submitted file
is permanently preserved regardless of validation outcome.

#### Implementation
- Azure Blob Storage SDK (azure-storage-blob Python package)
- Storage path: {container}/{domain}/{template_name}/
- Filename: {template_name}_{YYYYMMDD}_{HHMMSS}.{extension}
- Timestamp generated server side in FastAPI at moment of receipt
- Blob URL and storage path saved to upload_history record

### 5.3 File Validation

#### Decision
Two layer validation approach with clear separation of concerns:

Layer 1 — FastAPI validation using Polars (runs before Databricks)
  Purpose: fast cheap gate that catches errors before consuming
  Databricks compute. Gives user immediate row level feedback.
  Polars chosen over Pandas for superior performance on larger
  files and familiar lazy evaluation model (similar to Spark).

Layer 2 — DLT expectations in Databricks write job (runs at
  write time)
  Purpose: authoritative enforcement at Delta table level.
  DLT event log is the permanent record of what was actually
  written vs dropped.

#### What Layer 1 (Polars) validates
- Schema validation:
  - Column names match template definition exactly
  - Column count matches template definition
  - Delimiter and encoding match template config
  - Data types — attempt cast of each value to expected type,
    flag failures
- Constraint validation:
  - NOT NULL — rows where included column is empty or null
  - UNIQUE — duplicate detection using Polars groupby
    IMPORTANT: Delta Lake does NOT enforce UNIQUE constraints.
    Polars is the only enforcement layer for uniqueness.
    This must be clearly communicated to users.
- Bad row threshold:
  - Calculate bad_rows / total_rows as percentage
  - If exceeds threshold — return failure immediately,
    do not trigger Databricks job, save DBU cost
  - If within threshold and action is drop — filter bad rows,
    write clean subset to validated file path in Blob Storage
  - If within threshold and action is fail — return failure
    with full error report

#### What Layer 2 (DLT) validates and enforces
- NOT NULL enforced via DLT expect_or_drop on included columns
- CHECK constraints enforced via DLT expect_or_drop
- UNIQUE is NOT enforced at DLT layer — Delta limitation

#### How DLT event log powers the UI stepper
- After DLT pipeline completes FastAPI queries the DLT event
  log Delta table via Databricks SQL REST API
- Event log contains authoritative counts:
  - Total rows processed
  - Rows passed all expectations
  - Rows dropped by each expectation with counts
- These counts populate the final state of stepper Step 4
- This ensures the UI reflects what Databricks actually did —
  not what Polars predicted — making the event log the
  single source of truth for what landed in the UC table

#### Validation error report
- Row level errors collected during Polars validation (Layer 1)
- Stored in upload_validation_errors table in PostgreSQL
- Returned to UI as structured JSON for the error table
  in the progress stepper
- DLT event log summary appended to this report after
  Layer 2 completes

#### Why this separation makes sense
- Layer 1 is the fast cheap gate — runs in milliseconds,
  catches obvious problems, sends bad files back before
  any Databricks DBU cost is incurred
- Layer 2 is the authoritative enforcement layer — what
  actually happened is recorded permanently in the DLT
  event log and is the true record of what landed in UC
- A user or auditor can always query the DLT event log
  to see exactly what was written and what was rejected
  and why — independent of our application logs
### 5.4 Upload Progress UI

#### Decision
Progress driven by polling. FastAPI returns a job_id immediately
after receiving the upload. React polls GET /uploads/{job_id}/status
every 3 seconds. FastAPI returns current step and status.

#### Steps tracked
1. file_uploaded — set immediately when Blob write completes
2. schema_validated — set after Pandas schema check completes
3. constraints_checked — set after Pandas constraint check
   completes. Contains row level errors if any.
4. writing_to_catalog — set when Databricks job is submitted
5. completed — set when Databricks run_id shows success
6. failed — set at any step that produces a terminal failure

#### Implementation
- Upload state stored in PostgreSQL upload_history table
- Each step updates the status column and relevant counts
- React polls every 3 seconds and updates stepper UI

### 5.5 Data Write Job

#### Decision
DLT (Delta Live Tables) declarative pipeline used for the write
job. This is the appropriate place for DLT because:
- It involves ongoing data ingestion not one-time DDL
- DLT expectations provide a second enforcement layer for quality
- DLT event log provides quality metrics over time
- DLT handles append and overwrite modes natively

#### Implementation
- Separate DLT pipeline notebook stored in databricks/ folder
- Pipeline reads from the validated file path in Blob Storage
  (the clean subset written by FastAPI after Pandas validation)
- DLT expectations defined dynamically from template column
  configuration fetched from PostgreSQL
- Audit columns injected in the DLT pipeline as derived columns:
  - uploaded_by — passed as pipeline parameter
  - uploaded_at — current_timestamp()
  - source_file — passed as pipeline parameter
- Write mode (append/overwrite) configured via pipeline parameter
- FastAPI triggers pipeline via Databricks REST API and polls
  run_id for completion

### 5.6 Upload History

#### Implementation
- upload_history row created at start of upload with status
  in_progress
- Row updated at each validation step with counts and status
- upload_validation_errors rows inserted for each bad row found
- Final status set to success, failed or partial on completion

---

## 6. Authentication and Security

### Decision
Azure AD authentication using OAuth 2.0 authorization code flow.
MSAL (Microsoft Authentication Library) used on both frontend
and backend.

### Implementation
- React frontend uses @azure/msal-react package
- User logs in via Azure AD — receives JWT access token
- Every API request from React includes the token in the
  Authorization header: Bearer {token}
- FastAPI validates the token on every request using
  python-jose library
- User identity (email, name) extracted from validated token
- Identity used for created_by, uploaded_by audit fields

---

## 7. Technology Versions (locked)

| Technology        | Version  |
|-------------------|----------|
| Python            | 3.11     |
| FastAPI           | 0.110+   |
| SQLAlchemy        | 2.0+     |
| Alembic           | 1.13+    |
| Polars            | 1.38.1   |
| openpyxl          | 3.1.5    |
| fastexcel         | 0.12.1   |
| React             | 18+      |
| PostgreSQL        | 15       |
| Databricks Runtime| 14.3 LTS |
| Delta Lake        | 3.0+     |

---

## 8. API Design Conventions (locked)

- REST API — resource based URLs, standard HTTP methods
- All endpoints return JSON
- HTTP 200 — success with data
- HTTP 201 — resource created successfully
- HTTP 400 — bad request (validation error, invalid transition)
- HTTP 401 — unauthenticated
- HTTP 403 — authenticated but not authorized
- HTTP 404 — resource not found
- HTTP 500 — unexpected server error
- All timestamps in UTC
- All IDs are UUIDs
- Pagination on all list endpoints using limit and offset

---

## 9. Key Constraints and Limitations (locked)

- UNIQUE constraints are informational only in Delta Lake.
  Uniqueness is enforced exclusively in the FastAPI Pandas
  validation layer. This is a Delta Lake limitation and must
  be communicated to users.
- DLT pipelines cannot be triggered mid-flight by another
  pipeline. Each upload gets its own pipeline run.
- Approval tokens expire after 30 days.
- Maximum file size for upload: 100MB (configurable via env var)
- Supported file formats: CSV and Excel (.xlsx) only