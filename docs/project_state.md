# Manual File Uploader — Project State

This document is the authoritative snapshot of the project's
current state. Updated at the end of each phase. Read this
first when starting a new chat about this project.

---

## Project Vision

A self-service governance tool that turns scattered manual
mapping files (CSVs maintained by business users in email
chains) into governed, approved Unity Catalog tables.

Built for data engineering teams tired of chasing Excel
files over email.

The product is open source. Code lives at:
**[manual-file-uploader](https://github.com/github-mohsinalam/manual-file-uploader.git)**
(Update with your actual GitHub URL.)

---

## Project Owner

**Mohsin Alam** — Senior Data Engineer at an MNC, based in
Patna, India.

**Strong**: Python, Scala, Spark, SQL, Azure, Databricks,
DABs, Unity Catalog.

**Weak**: Web development (first time), FastAPI, React.

**Preference**: Wants every web dev concept explained from
scratch but respects existing data engineering knowledge.
Maps explanations to Spark/Scala when possible.

---

## Phase Progress

Phase 1  — Project scaffolding ✓ COMPLETE  
Phase 2  — PostgreSQL schema and SQL scripts ✓ COMPLETE  
Phase 3  — SQLAlchemy models ✓ COMPLETE  
Phase 4  — Azure infrastructure (storage, etc.) ✓ COMPLETE  
Phase 5  — Databricks DAB bundle, DDL job, UC catalog ✓ COMPLETE  
Phase 6  — Approval Workflow and Template API ✓ COMPLETE  
Phase 7  — Upload API ← IN PROGRESS  
Phase 8  — Entra ID auth (planned)  
Phase 9  — React frontend (planned)  
Phase 10 — Testing (planned)  
Phase 11 — Deployment to Azure Container Apps (planned)  
Phase 12 — Documentation polish + LinkedIn announcement (planned)  
Phase 13 — VNet peering exercise (bonus, planned)  

### Phase 7 Task Progress

Task 7.1  — Pydantic schemas for upload resources ✓ CLOSED  
Task 7.2  — POST /uploads endpoint scaffolding ✓ CLOSED  
Task 7.3  — Azure Blob Storage upload helper ✓ CLOSED  
Task 7.4  — Polars validation engine (Layer 1) ← NEXT  
Task 7.5  — Validation error recording  
Task 7.6  — Bad row threshold logic + staging Parquet write  
Task 7.7  — Databricks write job  
Task 7.8  — Databricks job trigger + polling  
Task 7.9  — Status tracking transitions  
Task 7.10 — Upload result email  
Task 7.11 — GET endpoints for uploads and errors  
Task 7.12 — End-to-end test  


---

## Time Constraint

Azure free trial has approximately 16 days remaining at
start of Phase 7. Priority is to finish end-to-end product
running on Azure before trial ends. Phase 12 documentation
can happen after trial expires.

Ambitious plan being followed:
- Phase 7 — 4 days (likely shorter with weekends)
- Phase 9 — 3 days (FULL React frontend, not toned down)
- Phase 11 — 2 days (deployment)
- Phase 12 — 2 days (documentation, can spill past trial)

Skipped during trial period:
- Phase 8 (real Entra ID auth) — keep stub for now
- Phase 10 (formal testing) — manual testing is enough
- Phase 13 (VNet peering) — bonus exercise

---

## Architectural Decisions Locked

These are NON-NEGOTIABLE without explicit re-discussion.

### Backend
- **Stack**: Python 3.11, FastAPI 0.110+, SQLAlchemy 2.0+, Pydantic 2.12.5
- **Database**: Azure PostgreSQL Flexible Server (development tier)
- **Storage**: Azure Data Lake Storage Gen2 (NOT plain Blob), accessed
  via `azure-storage-file-datalake` SDK
- **Auth (current)**: Stub via `get_current_user` dependency. Returns
  hardcoded user. Will be replaced with Entra ID JWT in Phase 8.
- **Email**: Azure Communication Services (NOT SMTP), with Jinja2
  templates. Sender name "MFU Notifications" via Azure-managed domain.
- **Background work**: FastAPI BackgroundTasks (NOT Celery, NOT RQ)
- **Validation**: Polars synchronous in FastAPI process

### Approval Workflow
- Creator is the requester, NEVER a reviewer of own template
- Required reviewers: ALL must approve
- Optional reviewers: notified, not blocking
- Tokens expire after 30 days
- Tokens are single-use (token_used flag)
- Approval action stored as past tense ('approved'/'rejected')
- URL paths use imperative verbs (/approve, /reject)
- On reject, template returns to Draft status
- On all-approved, template moves to Pending DDL → Approved
- Comment capture for reject deferred to React frontend (Phase 9)
- Reminder emails parked for future_improvements

### Databricks
- DABs (Databricks Asset Bundles) for resource deployment
- Serverless compute for jobs (no cluster management)
- One DDL job (one-time per template approval)
- Built-in retries handle transient failures (3 retries default)
- DLT/SDP NOT used. Decided in Phase 7 to use plain Spark job
  for upload writes after Polars handles all validation.

### File Upload Flow (Phase 7)
- Two-layer architecture:
  - Layer 1: Polars in FastAPI (sync, fast feedback)
  - Layer 2: Databricks Spark job (async, writes to UC)
- Single shared Databricks job reused per upload, parameterized
  with template_id and file_path
- File formats supported: CSV and XLSX (Polars handles both)
- Excel via Polars, NOT Spark (Spark Excel support is awkward)
- Max file size: 100 MB (settings.max_file_size_mb)
- Path scheme: uploads/{domain}/{template_id}/{upload_id}/{filename}
- UX pattern: Progress page with polling (8-status stepper)

### Status Values
**Templates** lifecycle:  
Draft → Pending Approval → Pending DDL → Approved → Deprecated  
↓&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↓  
Draft         DDL Failed  
(on reject)  

**Uploads** lifecycle:  
in_progress → file_uploaded → schema_validated → constraints_checked  
→ writing_to_catalog → completed  
→ failed  
→ partial (bad rows dropped)  

### upload_history Table Columns (Final)
We dropped redundant columns. Final shape stores:
- total_rows, valid_rows, invalid_rows (Polars layer)
- databricks_run_id (write phase tracking)
- status (8-state lifecycle)
- error_summary, completed_at, updated_at, uploaded_at
- file_size_bytes, original_filename, stored_filename, storage_path
- We do NOT have: dropped_rows, rows_written, rows_dropped,
  dlt_event_log_path. Information is derivable from status +
  valid_rows + invalid_rows.

---

## Project Structure

manual-file-uploader/  
├── backend/  
│   ├── app/  
│   │   ├── auth/  
│   │   │   ├── dependencies.py    (stub get_current_user)  
│   │   │   └── models.py          (User Pydantic)  
│   │   ├── core/  
│   │   │   └── config.py          (Pydantic Settings)  
│   │   ├── database/  
│   │   │   └── database.py        (engine, get_db)  
│   │   ├── models/                (8 SQLAlchemy models)  
│   │   │   ├── init.py  
│   │   │   ├── base.py            (TimestampMixin, CreatedAtMixin)  
│   │   │   ├── domain.py  
│   │   │   ├── template.py  
│   │   │   ├── template_column.py  
│   │   │   ├── template_reviewer.py  
│   │   │   ├── template_approval.py  
│   │   │   ├── upload_history.py  
│   │   │   └── upload_validation_error.py  
│   │   ├── schemas/               (Pydantic schemas)  
│   │   │   ├── init.py  
│   │   │   ├── common.py          (ORMBase, IdentifierStr, etc.)  
│   │   │   ├── domain.py  
│   │   │   ├── template.py  
│   │   │   ├── template_column.py  
│   │   │   ├── template_reviewer.py  
│   │   │   ├── template_approval.py  
│   │   │   ├── approval_action.py  
│   │   │   ├── upload_history.py  
│   │   │   └── upload_validation_error.py  
│   │   ├── routers/  
│   │   │   ├── health.py  
│   │   │   ├── domains.py  
│   │   │   ├── templates.py  
│   │   │   ├── template_columns.py  
│   │   │   ├── template_reviewers.py  
│   │   │   ├── approvals.py  
│   │   │   └── uploads.py  
│   │   ├── services/  
│   │   │   ├── email/             (ACS email service)  
│   │   │   ├── approval/          (workflow orchestration)  
│   │   │   ├── databricks/        (Databricks SDK wrapper)  
│   │   │   └── storage/  
│   │   │       ├── init.py  
│   │   │       └── storage_service.py    (ADLS Gen2)  
│   │   ├── email_templates/       (Jinja2 HTML templates)  
│   │   │   ├── test_email.html  
│   │   │   ├── approval_request.html  
│   │   │   ├── approval_decision.html  
│   │   │   ├── template_activation.html  
│   │   │   └── template_activation_failed.html  
│   │   └── main.py  
│   ├── sql/                       (9 numbered SQL scripts)  
│   ├── tests/                     (pytest)  
│   ├── requirements.txt  
│   └── .env (gitignored)  
├── databricks/  
│   ├── resources/  
│   │   └── jobs.yml               (DDL job)  
│   ├── src/  
│   │   └── ddl_job.py             (DDL job script)  
│   └── databricks.yml             (DAB config)  
├── azure_infra/  
│   ├── 01_create_resource_group.sh  
│   ├── 02_create_postgres.sh  
│   ├── 03_create_storage.sh  
│   ├── 04_create_databricks.sh  
│   ├── 05_create_unity_catalog.sh  
│   └── 06_create_acs_email.sh  
├── docs/  
│   ├── implementation_decisions.md  
│   ├── future_improvements.md  
│   └── project_state.md           (this file)  
├── pytest.ini  
└── .gitignore   

---

## Known Gotchas (Past Mistakes That Should NOT Repeat)

These are real bugs we hit during development. Future code
should NOT reintroduce these patterns.

1. **TemplateReviewer field names** — model uses `reviewer_email`,
   `reviewer_name`, `reviewer_type` (NOT `email`, `name`, `is_required`)

2. **TemplateApproval field names** — model uses `action`, `actioned_at`
   (NOT `status`, `approved_at`)

3. **Database stores past tense** — `'approved'`, `'rejected'`. URL
   paths use present tense `/approve`, `/reject`. Convert at the
   service boundary.

4. **upload_history uses uploaded_at** — NOT created_at. The model
   does NOT inherit TimestampMixin. It defines its own timestamps.

5. **SQLite in tests strips timezone info** — datetime comparisons
   need `.replace(tzinfo=timezone.utc)` if value comes from SQLite.

6. **BackgroundTasks instance is per-request** — cannot reuse across
   chained background tasks. New tasks must create their own context.

7. **Spark python_task does NOT inject dbutils** — must explicitly
   construct from notebook context.

8. **Pydantic regex must match SQL CHECK constraint** — drift between
   schema layer and database layer causes runtime errors. We
   maintained drift on `data_type` (BIGINT, LONG) until caught
   during testing. Always check both layers when adding values.

9. **Azure Storage is ADLS Gen2 with hierarchical namespace** —
   use `azure-storage-file-datalake` SDK, NOT `azure-storage-blob`.
   Endpoint is `*.dfs.core.windows.net`, NOT `*.blob.core.windows.net`.
   storage_service.py exists at backend/app/services/storage/.

10. **Approval count function must use past-tense value** — querying
    approvals must filter `action == 'approved'` not `'approve'`.

---

## Tech Stack Versions Locked

alembic==1.18.4  
annotated-doc==0.0.4  
annotated-types==0.7.0  
anyio==4.13.0  
azure-common==1.1.28  
azure-communication-email==1.0.0  
azure-core==1.39.0  
azure-mgmt-core==1.6.0  
azure-storage-blob==12.28.0  
azure-storage-file-datalake==12.17.0  
certifi==2026.2.25  
cffi==2.0.0  
charset-normalizer==3.4.7  
click==8.3.2  
colorama==0.4.6  
cryptography==46.0.7  
databricks-sdk==0.105.0  
dnspython==2.8.0  
email-validator==2.3.0  
et_xmlfile==2.0.0  
fastapi==0.135.3  
fastexcel==0.12.1  
google-auth==2.49.2  
greenlet==3.3.2  
h11==0.16.0  
idna==3.11  
iniconfig==2.3.0  
isodate==0.7.2  
Jinja2==3.1.4  
Mako==1.3.10  
MarkupSafe==3.0.3  
msrest==0.7.1  
oauthlib==3.3.1  
openpyxl==3.1.5  
packaging==26.0  
pluggy==1.6.0  
polars==1.38.1  
polars-runtime-32==1.38.1  
protobuf==6.33.6  
psycopg2-binary==2.9.11  
pyarrow==23.0.1  
pyasn1==0.6.3  
pyasn1_modules==0.4.2  
pycparser==3.0  
pydantic==2.12.5  
pydantic-settings==2.13.1  
pydantic_core==2.41.5  
pytest==8.3.3  
python-dotenv==1.2.2  
python-multipart==0.0.27  
requests==2.33.1  
requests-oauthlib==2.0.0  
SQLAlchemy==2.0.49  
starlette==1.0.0  
typing-inspection==0.4.2  
typing_extensions==4.15.0  
urllib3==2.6.3  
uvicorn==0.44.0  


---

## Working Conventions

### Decision Discipline
When 2+ valid options exist, the assistant STOPS, presents
trade-offs, and waits for the user's decision. Never writes
code on speculative paths.

### Mistake Patterns to Avoid
Before writing code that touches an existing model or service,
the assistant ASKS the user to share the relevant file rather
than assuming attribute names. Mistakes have been made earlier
on TemplateReviewer attributes and storage_service existence —
these caused rework. Asking is cheap, rework is not.

### Documentation Updates
- implementation_decisions.md updated at end of each phase
- future_improvements.md updated whenever scope is parked
- project_state.md (this file) updated at end of each phase

### Commit Cadence
After every closed task, commit changes with a clear message
prefixed with task number. Push to GitHub.

### Testing Approach
Manual via Swagger for development. Unit tests via pytest only
for critical isolated logic (e.g. token validation). End-to-end
test at the close of each phase.

---

## Open Questions / Things to Decide Soon


---

## Last Updated

Phase 7, end of Task 7.3.