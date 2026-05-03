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
- Sample file parsed in FastAPI using Polars — column names and
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

### 3.4 Creator Role in Approval Workflow

#### Decision
The template creator is the requester, not a reviewer. The
creator never approves their own template. The reviewer list
must contain at least one OTHER required reviewer for the
template to be submittable.

#### Implementation
- POST /templates/{id}/reviewers accepts a list of reviewers
- Reviewer email cannot match the creator's email - rejected
  with 400 if attempted
- POST /templates/{id}/submit verifies the template has at
  least one required reviewer before transitioning to
  Pending Approval status
- The creator receives notifications about the workflow
  (approval decision emails, activation email) but does
  not receive an approval request email for their own template

---

## 4. Unity Catalog Table Provisioning

### 4.1 DDL Job (triggered on template approval)

#### Decision
Non-declarative PySpark script (not DLT) used for the DDL job.
DLT is not appropriate here because the DDL job only runs once per
template approval and does not involve data ingestion. DLT pipelines
are designed for ongoing streaming or batch data flows not one-time
schema provisioning.

#### Deployment approach
All Databricks resources (DDL job, DLT pipeline, scheduled reminder
jobs) are deployed via Databricks Asset Bundles (DABs).

Rationale for DABs:
- Infrastructure as code - Databricks jobs defined in version
  controlled YAML not clicked through the UI
- One command deploys all Databricks resources consistently
- Lowers barrier for anyone cloning and setting up this open
  source tool - they run one command instead of configuring
  each job manually in the UI
- Aligns with modern Databricks engineering practice

#### Script format
All Databricks code written as plain .py Python scripts.

No notebook cell markers. No Databricks magic comments.
Just regular Python with a proper entry point:

    def main(template_id: str) -> None:
        # business logic
        ...

    if __name__ == "__main__":
        template_id = dbutils.widgets.get("template_id")
        main(template_id)

Rationale:
- Clean, readable code with no visual clutter
- Works as a regular Python module - can be imported and unit
  tested by pytest without requiring Databricks
- Standard Python project structure that any Python developer
  understands immediately
- Runs in Databricks as a job task with no special handling
  needed - Databricks executes .py files natively

The only Databricks specific elements are:
- dbutils.widgets.get() to read job parameters
- spark (automatically available in Databricks runtime)

Both are isolated to the entry point block so the core business
logic functions are pure Python that can be tested locally.

#### Implementation
- Python script stored in databricks/src/ddl_job.py
- Script defined as a job in databricks/databricks.yml
- Deployed to Databricks workspace via databricks bundle deploy
- FastAPI triggers the job via Databricks Jobs REST API
  (POST /api/2.1/jobs/runs/submit) using the job ID
- Script receives template_id as a parameter
- Script reads full template definition from PostgreSQL
- Script dynamically builds and executes CREATE TABLE using Spark SQL
- Column comments applied via ALTER TABLE ALTER COLUMN SET COMMENT
- PII masking applied via CREATE ROW FILTER / COLUMN MASK in UC
- NOT NULL enforced via ALTER TABLE ADD CONSTRAINT CHECK
  (column IS NOT NULL)
- UNIQUE constraint added as informational metadata only -
  NOT enforced by Delta Lake. Actual uniqueness enforced in
  Polars validation layer at upload time (see section 5.3)
- UC grants applied via GRANT SQL statements in the script:
  - USE CATALOG on manualuploads catalog
  - USE SCHEMA on the relevant schema
  - SELECT on the newly created table
- FastAPI polls job status via GET /api/2.1/jobs/runs/get
  using the run_id returned from job submission
- On job success FastAPI updates template status to
  Approved in PostgreSQL
- On job failure FastAPI updates template status to
  DDL Failed and notifies creator
- Grant handling is forgiving - if a reader group does
  not exist in Databricks, the specific grant is logged
  as a warning and skipped. Other grant failures remain
  fatal. Table creation and PII masking are not affected
  by missing groups.
- DDL job outcome (grants applied, grants skipped, PII
  applied, table FQN) is communicated to the template
  creator via the Template Activation email (see
  Section 6.4). Implementation deferred to Phase 6.

---

## 5. File Upload

### 5.1 Upload Flow

#### Decision
Two-layer architecture for separation of concerns:

Layer 1 — FastAPI + Polars (synchronous, fast user feedback)
  Validates the file completely. By the time the POST request
  returns, the file is uploaded to storage and validation is
  complete. The user sees immediate feedback.

Layer 2 — Databricks Spark job (asynchronous, background)
  Reads the validated clean data and writes to Unity Catalog
  Delta table. Triggered as a background task after Layer 1.
  User does not wait for this.

This split provides:
- Fast feedback to user on validation issues
- No Databricks compute consumed for invalid files
- Clean separation of validation and persistence

#### Implementation
- POST /uploads — multipart form endpoint receives template_id
  and file bytes
- Only Approved templates accepted (status check at endpoint level)
- File extension must match template's file_format setting
- File size limit enforced via settings.max_file_size_mb (100 MB)
- Returns UploadSummary with upload_id once Layer 1 completes
- Background task triggers Databricks Spark write job
- Frontend polls GET /uploads/{id} to track progress

### 5.2 File Storage

#### Decision
Raw file written to Azure Data Lake Storage Gen2 immediately on
receipt before any validation runs. This ensures every submitted
file is permanently preserved regardless of validation outcome.

ADLS Gen2 chosen over plain Blob Storage because:
- Real folders with atomic rename and delete operations
- Native Databricks and Unity Catalog integration
- POSIX style permissions per folder
- Efficient listing for deep hierarchies
- Same cost as plain Blob Storage at our scale

#### Implementation
- azure-storage-file-datalake SDK (NOT azure-storage-blob)
- Endpoint pattern: *.dfs.core.windows.net
- storage_service.py module under backend/app/services/storage/
  encapsulates all storage operations - rest of code never touches
  Azure SDK directly
- Storage path scheme:
  uploads/{domain_uc_schema_name}/{template_id}/{upload_id}/{filename}
- Original filename preserved (uniqueness comes from upload_id in path)
- Upload path stored in upload_history.storage_path column

### 5.3 File Validation (Layer 1 - Polars)

#### Decision
Polars used for ALL validation. No DLT/SDP expectations.
Polars chosen over Pandas for performance and lazy evaluation
familiar from Spark.

Note: Databricks rebranded DLT to Spark Declarative Pipelines (SDP)
in mid-2025. We evaluated SDP and decided not to use it for the
write step because:
- SDP would duplicate validation Polars already did
- SDP has poor native Excel support (would require third-party
  spark-excel library)
- A simple Spark write job is cleaner and has lower overhead
- We do not need SDP's incremental processing benefits

#### What Polars validates
- Schema validation:
  - Column names match template definition exactly
  - Column count matches template definition
  - Delimiter and encoding match template config
  - Data types — attempt cast of each value to expected type,
    flag failures
- Constraint validation:
  - NOT NULL — rows where included column is empty or null
  - UNIQUE — duplicate detection using Polars group_by
    IMPORTANT: Delta Lake does NOT enforce UNIQUE constraints.
    Polars is the ONLY enforcement layer for uniqueness.
- Excel files: read via Polars (uses fastexcel under the hood)
- CSV files: read via Polars native CSV reader
- Bad row threshold:
  - Calculate bad_rows / total_rows as percentage
  - If exceeds threshold and bad_row_action='fail' — return
    failure immediately, do not trigger Databricks job
  - If within threshold and action='drop' — filter bad rows,
    write clean subset to staging Parquet
  - If within threshold and action='fail' — proceed only if
    zero bad rows; otherwise return failure

#### Validation error report
- Row level errors collected during Polars validation
- Stored in upload_validation_errors table in PostgreSQL
- Returned to UI via separate GET /uploads/{id}/errors endpoint
  (paginated)
- POST /uploads response contains summary counts only

### 5.4 Upload Progress UI

#### Decision
Progress driven by polling. POST /uploads returns upload_id with
Layer 1 results synchronously. React polls GET /uploads/{upload_id}
every 2-3 seconds while watching status field. When status becomes
terminal (completed, failed, or partial), polling stops.

#### Steps tracked (8 status values)
1. in_progress — upload received, work just starting
2. file_uploaded — Blob upload complete
3. schema_validated — Polars schema check passed
4. constraints_checked — Polars constraint check complete
5. writing_to_catalog — Databricks write job triggered
6. completed — terminal, all rows written
7. failed — terminal, upload aborted
8. partial — terminal, some rows dropped (bad_row_action='drop')

The first four statuses transition synchronously during the POST
request. The last four are reached during/after the background
Databricks write job.

#### Implementation
- Upload state stored in PostgreSQL upload_history table
- Each step updates the status column and relevant counts
- React polls every 2-3 seconds and updates stepper UI
- Validation errors fetched separately if user wants details

### 5.5 Data Write Job (triggered after validation)

#### Decision
Plain Databricks Spark job (NOT DLT/SDP). Single shared job
parameterized per upload — created once via DABs deployment,
triggered with parameters for each upload.

Rationale for plain Spark over SDP:
- Polars already validated everything; SDP expectations would
  duplicate work
- Excel native support is in Polars, not Spark
- Simpler code — single Python script with Spark write
- Lower compute overhead - no SDP cluster startup
- We sacrifice SDP event log but Polars provides the same counts

#### Implementation
- Python script stored in databricks/src/upload_write_job.py
- Job defined in databricks/resources/jobs.yml as a Spark job
  on serverless compute
- Deployed via databricks bundle deploy alongside the DDL job
- Polars writes a clean Parquet file to staging path in ADLS:
  staging/{domain}/{template_id}/{upload_id}/data.parquet
- FastAPI triggers job via Databricks Jobs REST API with
  parameters: template_id, upload_id, staging_path,
  target_table_fqn, write_mode
- Spark script reads the Parquet, adds audit columns, writes
  to target Delta table
- Audit columns added by the Spark script:
  - uploaded_by - passed as job parameter
  - uploaded_at - current_timestamp()
  - upload_id - passed as job parameter
- Write mode (append/overwrite) configured via job parameter
- FastAPI polls run_id for completion, updates upload_history
  status accordingly

### 5.6 Upload History

#### Decision
upload_history table tracks every file upload with these final columns:

  Audit:
  - id, template_id, uploaded_by, uploaded_at, updated_at
  - original_filename, stored_filename, storage_path,
    file_size_bytes

  Validation results (Polars):
  - total_rows — input row count
  - valid_rows — passed all validation
  - invalid_rows — failed validation

  Lifecycle:
  - status — one of 8 status values
  - error_summary — failure reason (when status=failed)
  - completed_at — terminal timestamp

  Databricks tracking:
  - databricks_run_id — for the write job

We deliberately removed redundant columns during Phase 7 design:
- dropped_rows — same value as invalid_rows when action=drop
- rows_written — same as valid_rows on success, 0 on failure
  (Delta writes are atomic, no partial writes possible)
- rows_dropped — Spark realistically never drops rows after
  Polars validation, always 0
- dlt_event_log_path — no longer using DLT

All this information is derivable from valid_rows + invalid_rows
+ status. Avoiding redundancy keeps the schema simpler and
prevents drift.

#### Implementation
- upload_history row created at start of upload with status
  'in_progress'
- Row updated at each validation step with counts and status
- upload_validation_errors rows inserted for each bad row
  found during Polars validation
- Final status set to completed, failed, or partial
- error_summary populated only when status=failed
---

## 6. Email Notifications

All email notifications are sent by FastAPI using Azure
Communication Services (ACS) with an Azure-managed domain.
SMTP fallback option not implemented - decision was locked
on ACS during Phase 6 setup.

Emails use Jinja2 HTML templates stored in
backend/app/email_templates/. Sender display name is
"MFU Notifications". ACS connection string is read from
the AZURE_COMMUNICATION_CONNECTION_STRING environment
variable. All emails sent as background tasks (FastAPI
BackgroundTasks) so they do not block the HTTP response.

### 6.1 Approval Request Email

Sent to each required reviewer when a template is submitted
for approval.

Recipients: All required reviewers listed on the template

Trigger: Template submitted (status changes to 'Pending Approval')

Contents:
- Template creator name and email
- Template name, domain, and description
- Link to view the full template definition in the app
- Approve button (tokenized link, single-use, 30-day expiry)
- Reject button (tokenized link, single-use, 30-day expiry)
- Context on why they are a required reviewer

### 6.2 Approval Reminder Email

Sent on a daily schedule to reviewers who have not yet
acted on pending approval requests.

Recipients: Required reviewers with pending decisions

Trigger: FastAPI APScheduler runs daily at 9 AM. Queries
PostgreSQL for templates in 'Pending Approval' status older
than 3 days with reviewers who have not yet decided.

Contents:
- Days pending since approval request
- Template details
- Approve and Reject tokenized buttons (same tokens as
  original approval request email)

### 6.3 Approval Decision Email

Sent to the template creator when any reviewer approves
or rejects.

Recipients: Template creator

Trigger: Reviewer clicks approve or reject link

Contents:
- Reviewer name and decision
- Reviewer comment (if any)
- Current overall status of the template (how many
  approvals still needed, or rejected)
- Link to view the template in the app

### 6.4 Template Activation Email

Sent to the template creator when the DDL job completes
successfully and the Unity Catalog table is ready to use.

Recipients: Template creator

Trigger: FastAPI receives successful completion signal
from the Databricks DDL job and updates template status
to 'Active'

Contents:
- Template name and version
- Fully qualified Unity Catalog table name
- Status of grants (applied / skipped with reason)
- Status of PII masking (applied / not applicable)
- Link to view the table in Databricks Catalog
- Link to view the template in the app
- Information on how to upload the first file

### 6.5 Upload Result Email

Sent to the uploader after a file upload completes or fails.

Recipients: User who uploaded the file

Trigger: FastAPI receives completion signal from the write
pipeline

Contents:
- Template name and table
- Upload outcome (success / partial / failed)
- Row counts (total, valid, bad)
- Link to view upload history in the app
- If failed, the reason and next steps

---

## 7. Authentication and Security

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

## 8. Technology Versions (locked)

| Technology         | Version   |
|--------------------|-----------|
| Python             | 3.11      |
| FastAPI            | 0.110+    |
| SQLAlchemy         | 2.0+      |
| Alembic            | 1.13+     |
| Polars             | 1.38.1    |
| openpyxl           | 3.1.5     |
| fastexcel          | 0.12.1    |
| React              | 18+       |
| PostgreSQL         | 15        |
| Databricks Runtime | 14.3 LTS  |
| Delta Lake         | 3.0+      |

---

## 9. API Design Conventions (locked)

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

## 10. Key Constraints and Limitations (locked)

- UNIQUE constraints are informational only in Delta Lake.
  Uniqueness is enforced exclusively in the FastAPI Polars
  validation layer. This is a Delta Lake limitation and must
  be communicated to users.
- Approval tokens expire after 30 days.
- Approval tokens are single-use - once actioned cannot be
  reused.
- Maximum file size for upload: 100MB (configurable via
  MAX_FILE_SIZE_MB env var).
- Supported file formats: CSV and Excel (.xlsx) only.
- Excel reading is done in Polars (FastAPI), not Spark
  (Databricks). Spark Excel support requires third-party
  libraries; we keep Excel handling on the Polars side
  exclusively.
- BackgroundTasks are scoped to a single HTTP request.
  Cannot be reused across chained background tasks. Each
  background task that schedules further async work must
  do so by calling the function directly, not via
  BackgroundTasks.add_task() outside its request scope.
- DDL polling task is in-memory. If FastAPI restarts
  mid-poll, the task is lost. Crash recovery deferred -
  see future_improvements.md.
- Approval reminder emails not implemented - parked in
  future_improvements.md.