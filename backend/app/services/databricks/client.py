"""
Databricks client wrapper.

Centralizes all interaction with the Databricks Jobs API.
Other code calls these helpers - never imports databricks-sdk
directly.

Authentication uses DATABRICKS_HOST and DATABRICKS_TOKEN from
settings.
"""

import logging
from functools import lru_cache

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import Run

from app.core.config import settings


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_workspace_client() -> WorkspaceClient:
    """
    Return a singleton WorkspaceClient configured from settings.

    """
    if not settings.databricks_host or not settings.databricks_token:
        raise ValueError(
            "DATABRICKS_HOST and DATABRICKS_TOKEN must be configured"
        )

    return WorkspaceClient(
        host=settings.databricks_host,
        token=settings.databricks_token,
    )


def trigger_ddl_job(template_id: str) -> int:
    """
    Trigger the DDL job for an approved template.

    Returns the run_id of the triggered Databricks job run.
    The caller can poll for status using this ID later.

    Raises any exception from the underlying SDK call - the
    SDK has built-in retries for transient errors so by the
    time an exception escapes, retries are exhausted.

    Args:
        template_id: UUID string of the approved template

    Returns:
        Databricks run_id (integer)
    """
    if not settings.databricks_ddl_job_id:
        raise ValueError("DATABRICKS_DDL_JOB_ID is not configured")

    client = get_workspace_client()

    job_id = int(settings.databricks_ddl_job_id)

    logger.info(
        f"Triggering DDL job {job_id} for template {template_id}"
    )

    run = client.jobs.run_now(
        job_id=job_id,
        job_parameters={"template_id": str(template_id)},
    )

    # The SDK returns a Wait object
    # we fetch the run_id from the Wait itself
    run_id = run.run_id

    logger.info(
        f"DDL job triggered.job_id={job_id} ; run_id={run_id} ; template={template_id}"
    )

    return run_id


def get_run_status(run_id: int) -> Run:
    """
    Get the current status of a Databricks job run.

    Used by the polling background task in Task 6.11.

    Returns the full Run object - caller inspects .state to
    determine if it is still running, succeeded, or failed.
    """
    client = get_workspace_client()
    return client.jobs.get_run(run_id=run_id)