# Future Improvements

This document tracks features, improvements, and known
limitations to address in future versions of the Manual File
Uploader.

Items here are intentionally NOT in the current scope but
are worth implementing eventually.

## Recovery and Reliability

### DDL polling task crash recovery

**Problem:**
The current implementation polls Databricks for DDL job
completion in a background task. If the FastAPI server
crashes or restarts mid-poll, the task is lost. The
Databricks job continues to completion but the template
stays stuck in `Pending DDL` status.

**Proposed solution:**
A periodic scheduler job (APScheduler or similar) that runs
every 5 minutes and queries the database for templates in
`Pending DDL` status with a non-null `databricks_ddl_run_id`.
For each one, it queries the Databricks run status and
processes the same way the original polling task would have.

**Effort estimate:** ~2 hours

## UI/UX
### Approval email content
**Problem:**
The current email sent to approver conatins basic details like table name and domain.It doesn't give any details about the template's column.

**Proposed solution:**
We can add a JSON view to capture column details .

## Reliability

### Upload polling task crash recovery

**Problem:**
Same as the DDL polling task crash recovery item. After
the upload write job is triggered, FastAPI polls Databricks
in a background task. If the FastAPI server crashes or
restarts mid-poll, the task is lost. The Databricks job
continues to completion but the upload stays stuck in
`writing_to_catalog` status with `databricks_run_id`
populated.

**Proposed solution:**
Extend the periodic scheduler job already proposed for DDL
recovery to also handle uploads. Query the database for
upload_history rows in `writing_to_catalog` status with a
non-null `databricks_run_id`, fetch each Databricks run
status, and finalize each row the same way the original
poller would have.

**Effort estimate:** ~1 hour on top of the DDL recovery
work. Same code shape, different table.

## Code Organization

### Rename services/validation to services/upload

**Problem:**
The directory `backend/app/services/validation/` contains
the validator (correct), the upload pipeline orchestrator,
the upload-result email helpers, and the upload polling
task. Three of those four are upload-flow concerns, not
validation concerns. The naming has drifted.

**Proposed solution:**
Rename the directory to `services/upload/`. Update every
import (about 5-8 files in routers and the package
itself). Files inside stay - just the package name moves.

**Effort estimate:** ~30 minutes including a full test
sweep to confirm no regressions.

## Validation

### Stricter CSV row-shape validation

**Problem:**
Polars' CSV reader is lenient by default. A file with
mismatched quotes that the parser can recover from passes
through to schema validation, where the structurally bad
data may or may not surface depending on how Polars chose
to interpret it. Real example caught during Phase 7
testing: a row like `2,"Student_2',82` did not raise
PARSE_ERROR; instead Polars parsed surrounding rows
incorrectly.

**Proposed solution:**
Pre-validate row-shape consistency before handing bytes
to Polars. Count delimiters per raw line; raise
PARSE_ERROR if any line has a different field count
from the header. Cheap to implement, catches realistic
corruption cases.

**Effort estimate:** ~30 minutes.

## Authorization

### Scope upload reads to the uploader

**Problem:**
GET /uploads, GET /uploads/{id}, and GET /uploads/{id}/errors
are open to any authenticated caller. Any user can list
or fetch any upload regardless of who created it. Same
pattern is in place for templates listing.

This was an explicit decision during development. Tightening it later means adding
filters like `WHERE uploaded_by = current_user.email`
to each GET endpoint, plus a 403 path when a user tries
to fetch by ID an upload they did not create.

**Proposed solution:**
Add per-row authorization on all upload GET endpoints.
Either tighten unconditionally (each user sees only
their own) or add a role-based override (admins see
everything). Decision pending - probably worth a short
discussion before implementing.

**Effort estimate:** 1-2 hours including pytest coverage
for the new permission paths.

## Backend Validation

### Scope template name uniqueness to domain

**Problem:**
The backend currently enforces template name uniqueness
globally - the SQL UNIQUE constraint is on
`fully_qualified_name` but the FastAPI router uses an
extra Python-level check that compares only `name`. This
means `region_mapping` in Finance prevents `region_mapping`
in Sales from existing, even though they target different
Unity Catalog schemas and are unrelated entities.

The fully_qualified_name uniqueness (which IS scoped to
domain since it includes the schema) already provides
correct database-level protection. The extra Python check
in templates.py is what causes the over-restriction.

**Proposed solution:**
In `app/routers/templates.py`, change
`_check_template_name_unique` to scope by domain:

    query = db.query(Template).filter(
        Template.name == name,
        Template.domain_id == domain_id,
    )

Pass the domain_id from the create call. The check
becomes: "no other template in THIS domain has THIS name".
Update the error message accordingly.

The same check on PATCH (template update) needs the same
treatment.

**Effort estimate:** ~20 minutes including a quick test.

## Documentation

### End-to-end journey diagrams and narratives

**Problem:**
The project has many moving parts spread across backend
routes, services, the React frontend, Databricks job triggers,
and Unity Catalog. Understanding the full lifecycle of a
template - from creation through approval, DDL provisioning,
file upload, validation, and final Delta-table state - requires
reading multiple files in multiple folders. There is no
single document that traces the journey end-to-end.

**Proposed solution:**
Produce a `docs/end_to_end_flows.md` file capturing each
major user journey as a numbered, plain-English flow:

1. Template creation journey (Draft to active UC table)
   - Creator submits wizard
   - Approval emails dispatched
   - Reviewers decide via frontend approval page
   - DDL job runs in Databricks
   - Creator receives activation email
   - Template is Approved, ready for uploads

2. File upload journey (uploaded CSV/XLSX to Delta row insert)
   - Upload submitted via frontend
   - File stored in Azure Blob
   - Polars Layer 1 validation
   - Databricks upload job triggered
   - PySpark/Delta write completes
   - Validation errors persisted (if any)
   - Upload status moves to terminal state

3. Approval flow (reviewer journey)
   - Email arrives
   - Click Approve in email
   - Land on frontend approval page (no login)
   - Review template details
   - Add optional comment
   - Confirm decision
   - Already-decided revisits handled gracefully

Each flow should include:
- Numbered step-by-step narrative
- File-level references for readers who want to dig in
  (e.g. "approvals.py /approvals/{token}/approve")
- A simple ASCII or mermaid sequence diagram showing the
  hops between Frontend, FastAPI, PostgreSQL, Azure Blob,
  Databricks, and ACS

**Use cases:**
- Onboarding new contributors quickly
- Reference material for the LinkedIn announcement and
  demo video script
- Embedded in README as a "How it works" section
- Help during debugging - given a step where things went
  wrong, the doc tells you which files to check first

**Effort estimate:** ~3 hours total for all three flows
with diagrams. Best done at the END of Phase 9 once the
whole user-facing journey is built and verifiable. Could
land as part of Phase 12 (Documentation polish) or as a
standalone task.