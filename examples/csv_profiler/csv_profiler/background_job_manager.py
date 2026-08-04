"""Domain submit wrapper for the CSV profiler computation task.

Thin wrapper over the framework's generic ``submit_named_job``; mounted on the
framework Job via ``Job.submit_handler`` at startup.
"""

from cosmo_suite.background_job_manager import background_job_manager

NAME_COMPUTATION_TASK = "csv_profiler.tasks.computation_tasks.start_computation"


def submit_computation_job(job) -> tuple[str | None, bool]:
    """Submit a CSV profiling job to the computation queue.

    Returns:
        tuple: (celery_task_id, failed_boolean); task_id is None on failure.
    """
    return background_job_manager.submit_named_job(
        NAME_COMPUTATION_TASK,
        args=[job.job_id],
        queue="computation",
    )
