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
