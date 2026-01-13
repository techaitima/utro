"""
APScheduler service for job scheduling.
Handles daily morning post scheduling.
"""

import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

from config import config

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create scheduler instance."""
    global scheduler
    if scheduler is None:
        timezone = pytz.timezone(config.timezone)
        scheduler = AsyncIOScheduler(timezone=timezone)
    return scheduler


def _job_listener(event: JobExecutionEvent) -> None:
    """Listen for job execution events and log them."""
    if event.exception:
        logger.error(
            f"Job {event.job_id} failed with exception: {event.exception}",
            exc_info=True
        )
    else:
        logger.info(f"Job {event.job_id} executed successfully")


def start_scheduler(
    morning_post_job: Callable[[], Awaitable[None]]
) -> AsyncIOScheduler:
    """
    Start the scheduler with the morning post job.
    
    Args:
        morning_post_job: Async function to call for morning posts
    
    Returns:
        The running scheduler instance
    """
    sched = get_scheduler()
    
    # Add job listener for logging
    sched.add_listener(_job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # Parse post time from config
    hour = config.get_post_hour()
    minute = config.get_post_minute()
    
    # Create cron trigger for daily execution at specified time
    trigger = CronTrigger(
        hour=hour,
        minute=minute,
        timezone=pytz.timezone(config.timezone)
    )
    
    # Add the morning post job
    sched.add_job(
        morning_post_job,
        trigger=trigger,
        id="morning_post",
        name="Daily Morning Post",
        replace_existing=True,
        misfire_grace_time=3600  # Allow 1 hour grace time for missed jobs
    )
    
    # Start the scheduler
    sched.start()
    
    # Log next run time
    job = sched.get_job("morning_post")
    if job and job.next_run_time:
        logger.info(
            f"Scheduler started. Next morning post: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )
    else:
        logger.info("Scheduler started")
    
    return sched


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
    scheduler = None


def get_next_run_time() -> Optional[datetime]:
    """Get the next scheduled run time for morning post."""
    sched = get_scheduler()
    job = sched.get_job("morning_post")
    if job:
        return job.next_run_time
    return None


def trigger_job_now() -> bool:
    """
    Trigger the morning post job immediately.
    
    Returns:
        True if job was triggered, False otherwise
    """
    sched = get_scheduler()
    job = sched.get_job("morning_post")
    if job:
        sched.modify_job("morning_post", next_run_time=datetime.now(pytz.timezone(config.timezone)))
        logger.info("Morning post job triggered manually")
        return True
    return False


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    sched = get_scheduler()
    return sched.running if sched else False


def get_all_jobs_info() -> list:
    """Get information about all scheduled jobs."""
    sched = get_scheduler()
    jobs = []
    for job in sched.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z") if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    return jobs
