"""Celery tasks for Cenex AI."""

from app.tasks.market_data_tasks import (
    update_market_data,
    backfill_historical_data,
    backfill_all_symbols
)
from app.tasks.performance_tasks import (
    update_signal_performance,
    check_retraining_triggers,
    generate_performance_report,
    retrain_models,
    compute_single_outcome
)

__all__ = [
    # Market data tasks
    "update_market_data",
    "backfill_historical_data",
    "backfill_all_symbols",
    # Performance memory tasks
    "update_signal_performance",
    "check_retraining_triggers",
    "generate_performance_report",
    "retrain_models",
    "compute_single_outcome",
]
