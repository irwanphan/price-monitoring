from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Celery app configuration
celery_app = Celery(
    "price_monitor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jakarta",
    enable_utc=True,
    
    # Schedule: Run scraping every Monday at 6 AM (weekly report)
    beat_schedule={
        "weekly-price-scrape": {
            "task": "app.tasks.scraping_tasks.run_weekly_scraping",
            "schedule": crontab(hour=6, minute=0, day_of_week=1),  # Monday 6 AM
        },
        "daily-anomaly-check": {
            "task": "app.tasks.scraping_tasks.run_anomaly_check",
            "schedule": crontab(hour=8, minute=0),  # Every day 8 AM
        }
    }
)
