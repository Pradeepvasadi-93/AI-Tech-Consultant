"""Run the incremental sitemap ingestion once per day.

For production, a platform cron/scheduled job is also acceptable; keep one scheduler
instance only to avoid overlapping full crawls.
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from rag.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO)
SITEMAP_URL = "https://support.brilliantdirectories.com/support/sitemap.xml"


def ingest_daily():
    logging.info("Starting daily Knowledge Brain sitemap sync")
    result = run_pipeline(
        url=SITEMAP_URL,
        mode="sitemap",
        max_pages=None,
        delay=1.0,
        process_images=True,
        wipe=False,
    )
    logging.info("Daily Knowledge Brain sync finished: %s", result)


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        ingest_daily,
        trigger="cron",
        hour=2,
        minute=0,
        id="knowledge-brain-daily-ingestion",
        max_instances=1,
        coalesce=True,
    )
    logging.info("Daily ingestion scheduled for 02:00 UTC")
    scheduler.start()
