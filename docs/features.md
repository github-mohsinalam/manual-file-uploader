# Manual File Uploader — Complete Feature List

## 1. Domain Management

- Predefined list of business domains (Finance, HR, Supply Chain etc.)
- Each domain maps to a dedicated schema in Unity Catalog
- Domain name automatically sanitized to a UC-compatible schema name
  (e.g. "Supply Chain" → "supply_chain")

---

## 2. Template Management

### 2.1 Template Creation
- User provides a template display name and description
- User selects a business domain from a dropdown
- Fully qualified UC table name is auto-generated from:
  catalog name + domain schema + template name
  (e.g. manualuploads.finance.region_mapping)
- Real-time validation to check the template name does not already
  exist in the catalog — prevents name collisions before submission
- User selects file format: CSV or Excel (.xlsx)
- User configures delimiter (comma, pipe, tab) for CSV files
- User configures file encoding (UTF-8 etc.)
- User uploads a sample file during template creation
  - Sample file can contain just headers or a few rows of data
- System parses the sample file and displays all detected columns
- User selects which columns to include (individual or all)
- User provides a description for each included column
  - Column descriptions are stored and later applied as comments
    on the Unity Catalog table columns
- User configures each column:
  - Data type (STRING, INTEGER, DATE, TIMESTAMP, DECIMAL etc.)
  - PII flag — marks column as containing personally identifiable
    information
  - NOT NULL constraint
  - UNIQUE constraint
- User configures write mode: Append or Overwrite
- User configures bad row threshold (e.g. 5%)
  - This is the maximum percentage of invalid rows acceptable
    before the upload is rejected
- User configures bad row action:
  - Fail — reject the entire upload if any rows fail validation
  - Drop — drop invalid rows and write the remaining valid rows
    as long as they are within the threshold
- User provides the name of the reader group (Azure AD group)
  that will have SELECT access to the UC table
- User configures required reviewers (must approve before template
  goes live — creator is a required reviewer by default)
- User configures optional reviewers (notified but their approval
  is not a gate)

### 2.2 Template Versioning
- Editing an approved template never modifies the original
- Editing creates a new version of the template that goes through
  the full approval workflow again
- Each version stores a reference to its parent template
- Version number incremented automatically on each edit

### 2.3 Template Status Lifecycle
- Draft — template created but approval not yet triggered
- Pending Approval — approval request sent to reviewers
- Approved — all required reviewers approved and UC table created
- Rejected — at least one required reviewer rejected the template
- Deprecated — template manually retired by the owner

### 2.4 Template Listing Page
- Table view of all templates visible to the user
- Shows template name, domain, status, version, created by,
  created date
- Status shown as color coded badges
- Action icons per template row:
  - View — read only view of full template configuration
  - Approve — only visible to reviewers with pending action
  - Edit — creates a new version of the template

---

## 3. Approval Workflow

### 3.1 Reviewer Configuration
- Creator is always a required reviewer by default
- Creator can add additional required reviewers by email
- Creator can add optional reviewers by email
- Optional reviewers are notified but do not block approval

### 3.2 Approval Process
- On template submission an approval email is sent to all
  reviewers (required and optional)
- Email contains a direct link to the template with a unique
  secure token
- Required reviewers can:
  - Approve — records approval with timestamp
  - Reject — records rejection with mandatory comment
- Optional reviewers can provide feedback but their action
  does not change the template status
- Template moves to Approved only when ALL required reviewers
  have approved
- If any required reviewer rejects the template moves to
  Rejected and the creator is notified with the rejection reason
- Approval audit trail stored permanently — who approved,
  when and any comments

### 3.3 Approval Notifications
- Email sent to all reviewers when approval is requested
- Email sent to creator when template is approved
- Email sent to creator when template is rejected with reason
- Automatic reminder email sent to pending required reviewers
  after a configurable number of days with no action

### 3.4 Approval Security
- Each approval link contains a unique secure token
- Token is validated by the backend before recording any action
- Prevents approval by URL guessing

---

## 4. Unity Catalog Table Provisioning

### 4.1 DDL Job (triggered on template approval)
- Reads approved template definition from PostgreSQL
- Dynamically builds a CREATE TABLE statement
- Catalog = manualuploads (centralized for all manual files)
- Schema = derived from domain (e.g. finance)
- Table = template name (e.g. region_mapping)
- Column definitions include data type from template configuration
- Column comments applied from user provided descriptions
- PII columns get an additional comment flagging them as masked
- Audit columns auto-injected into every table regardless of
  user configuration:
  - uploaded_by — who uploaded the file
  - uploaded_at — timestamp of the upload
  - source_file — original filename with timestamp
- NOT NULL and UNIQUE constraints applied as Delta table constraints
- Column masking policy applied to all PII flagged columns
  using Unity Catalog native masking
- Permissions granted to the reader group:
  - USE CATALOG on manualuploads catalog
  - USE SCHEMA on the relevant schema
  - SELECT on the newly created table
- Job reports success or failure back to FastAPI via run_id polling
- Template status updated to Approved and Active on success

---

## 5. File Upload

### 5.1 Upload Flow
- User selects domain from dropdown
- User selects template from dropdown
  - Only Approved and Active templates appear in this dropdown
  - Prevents uploads to unapproved templates at the UI level
- User browses and selects a file from their local machine

### 5.2 File Storage
- Raw file immediately written to Azure Blob Storage on receipt
- Stored in a dedicated folder per template:
  manualfileuploads/{domain}/{template_name}/
- Filename has timestamp automatically appended:
  {template_name}_{YYYYMMDD}_{HHMMSS}.{extension}
- Original file preserved permanently in Blob Storage regardless
  of whether validation passes or fails
- Provides a permanent audit trail of every file ever submitted

### 5.3 File Validation
- Schema validation:
  - Column names match template definition
  - Column count matches template definition
  - Data types match template definition
  - Delimiter and encoding match template configuration
- Constraint validation per column:
  - NOT NULL — flags rows where a required column is empty
  - UNIQUE — flags rows where a unique column has duplicate values
  - Data type — flags rows where a value cannot be cast to the
    expected type
- Bad row threshold logic:
  - Calculates percentage of rows that failed any validation rule
  - If percentage exceeds configured threshold — entire upload
    fails regardless of bad row action setting
  - If percentage is within threshold:
    - Fail action — entire upload still fails
    - Drop action — bad rows are dropped, valid rows proceed
      to write

### 5.4 Upload Progress UI
- Step by step progress indicator shown in real time:
  - Step 1: File uploaded to Blob Storage
  - Step 2: Schema validation — pass or fail with details
  - Step 3: Constraint checks — pass, fail or warning with
    row level error table
  - Step 4: Write to Unity Catalog — in progress, success
    or warning
- Validation error report displayed on failure:
  - Row number, column name, rule violated, actual bad value
- Warning state shown when upload succeeds but rows were dropped
  - Summary shows how many rows were written and how many dropped

### 5.5 Data Write Job (triggered on validation pass)
- Databricks job reads validated file from Blob Storage
- Applies write mode (append or overwrite) per template config
- Auto-injects audit columns before write:
  - uploaded_by populated from authenticated user identity
  - uploaded_at populated with current timestamp
  - source_file populated with timestamped filename
- Writes data as a Delta table in Unity Catalog
- Job status polled via Databricks run_id

### 5.6 Upload History
- Every upload attempt recorded in PostgreSQL regardless of
  outcome including failures
- Record contains:
  - Who uploaded and when
  - Original filename and stored filename with timestamp
  - Full Blob Storage path
  - File size in bytes
  - Total rows, valid rows, invalid rows
  - Final status (success, failed, partial)
  - High level error summary
  - Databricks run_id for traceability
  - Completion timestamp

---

## 6. Authentication and Security

- Azure AD integration for user authentication
- All API endpoints protected — require valid Azure AD token
- User identity extracted from token for:
  - Audit columns (uploaded_by)
  - Template ownership (created_by)
  - Approval tracking (who approved)
- Approval links secured with unique per-reviewer tokens
- Secrets managed via environment variables — never hardcoded

---

## 7. Data Governance

- All manual mapping tables centralized in one Unity Catalog:
  manualuploads
- Domain based schema separation within the catalog
- PII columns automatically masked using Unity Catalog column
  masking policies
- Reader group access controlled at table level via UC grants
- Full audit trail for every template creation, approval action
  and file upload
- Template versioning ensures schema changes are governed and
  approved before taking effect
- Bad row threshold enforces minimum data quality standards
  per template

---

## 8. Non-Functional Features

- Cloud provider: Microsoft Azure
- Databricks REST API used for async job triggering
  - FastAPI submits job and receives run_id immediately
  - UI polls job status via run_id — drives progress stepper
- Configurable via environment variables for easy deployment
- Docker based local development environment
- Open source — MIT License
- Designed to be extended to support AWS and GCP in future
  via adapter pattern

---

## Out of Scope (for now — potential future features)

- Role based access control beyond reader group (e.g. editor,
  admin roles within the tool itself)
- Scheduled automatic uploads (currently manual only)
- API based uploads (currently UI only)
- Support for AWS S3 and GCS storage adapters
- Support for AWS Glue and GCP Data Catalog
- Slack or Teams notifications alongside email
- Data profiling and statistics on uploaded files
- Soft delete and archive for templates