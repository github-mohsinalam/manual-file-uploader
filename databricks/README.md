# Databricks Asset Bundle

This folder contains the Databricks Asset Bundle (DAB) that
deploys all Databricks resources required by the Manual File
Uploader application.

## Resources Deployed

- **DDL Job** — Creates Unity Catalog tables when templates
  are approved in the application
- **Write Pipeline (DLT)** — Writes validated file data into
  Unity Catalog Delta tables
- **Reminder Email Job** — Scheduled daily job for approval
  reminders

## Prerequisites

- Databricks CLI installed locally:
  `winget install Databricks.DatabricksCLI`
- Databricks workspace configured:
  `databricks configure --token`
- Unity Catalog created (see databricks/src/setup_catalog.py)

## Deploy

```bash
cd databricks
databricks bundle deploy --target dev
```

## Run a Job

```bash
databricks bundle run --target dev ddl_job
```

## View Status

```bash
databricks bundle summary --target dev
```

## Structure

- `databricks.yml` — main bundle configuration
- `src/` — Python source for jobs and pipelines
- `resources/` — YAML files defining jobs and pipelines
- `tests/` — unit tests for the Python code