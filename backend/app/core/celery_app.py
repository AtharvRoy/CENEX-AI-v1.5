"""
Celery application configuration for Cenex AI.
Handles scheduled tasks and async job processing.
"""

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "cenex_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.market_data_tasks',
        'app.tasks.maintenance_tasks',
        'app.tasks.performance_tasks'
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'update-market-data': {
        'task': 'app.tasks.market_data_tasks.update_market_data',
        # Every 15 minutes during market hours (9:00 AM - 3:30 PM IST, Mon-Fri)
        'schedule': crontab(minute='*/15', hour='9-15', day_of_week='mon-fri'),
        'options': {'queue': 'market_data'}
    },
    'cleanup-redis-cache': {
        'task': 'app.tasks.maintenance_tasks.cleanup_redis_cache',
        # Daily at 2:00 AM IST
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'maintenance'}
    },
    'check-data-quality': {
        'task': 'app.tasks.maintenance_tasks.check_data_quality',
        # Daily at 4:00 PM IST (after market close)
        'schedule': crontab(hour=16, minute=0, day_of_week='mon-fri'),
        'options': {'queue': 'maintenance'}
    },
    # Performance Memory Tasks (Layer 6 - Self-Learning Loop)
    'update-signal-performance': {
        'task': 'app.tasks.performance_tasks.update_signal_performance',
        # Daily at 5:00 PM IST (after market close)
        'schedule': crontab(hour=17, minute=0, day_of_week='mon-fri'),
        'options': {'queue': 'performance'}
    },
    'generate-performance-report': {
        'task': 'app.tasks.performance_tasks.generate_performance_report',
        # Daily at 6:00 PM IST
        'schedule': crontab(hour=18, minute=0, day_of_week='mon-fri'),
        'options': {'queue': 'performance'}
    },
    'check-retraining-triggers': {
        'task': 'app.tasks.performance_tasks.check_retraining_triggers',
        # Weekly on Sunday at 6:00 PM IST
        'schedule': crontab(hour=18, minute=0, day_of_week='sun'),
        'options': {'queue': 'performance'}
    },
}

# Queue routing
celery_app.conf.task_routes = {
    'app.tasks.market_data_tasks.*': {'queue': 'market_data'},
    'app.tasks.maintenance_tasks.*': {'queue': 'maintenance'},
    'app.tasks.performance_tasks.*': {'queue': 'performance'},
}
