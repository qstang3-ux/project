import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.database import new_session
from app.models import QaExecution, QaExecutionEvent
from app.services.execution_events import TERMINAL_STATUSES


@dataclass(frozen=True)
class CleanupResult:
    executions: int
    events: int


def cleanup_execution_events(days: int, limit: int) -> CleanupResult:
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    cutoff = datetime.now(UTC) - timedelta(days=days)
    with new_session() as db:
        execution_ids = list(
            db.scalars(
                select(QaExecution.id)
                .where(
                    QaExecution.status.in_(TERMINAL_STATUSES),
                    QaExecution.completed_at < cutoff,
                    select(QaExecutionEvent.id)
                    .where(QaExecutionEvent.execution_id == QaExecution.id)
                    .exists(),
                )
                .order_by(QaExecution.completed_at, QaExecution.id)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        deleted_events = 0
        for execution_id in execution_ids:
            latest_sequence = int(
                db.scalar(
                    select(func.max(QaExecutionEvent.sequence)).where(
                        QaExecutionEvent.execution_id == execution_id
                    )
                )
                or 0
            )
            execution = db.get(QaExecution, execution_id)
            if execution is None or latest_sequence == 0:
                continue
            execution.event_sequence_floor = max(execution.event_sequence_floor, latest_sequence)
            result = db.execute(
                delete(QaExecutionEvent).where(QaExecutionEvent.execution_id == execution_id)
            )
            deleted_events += int(result.rowcount or 0)
        db.commit()
    return CleanupResult(len(execution_ids), deleted_events)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Delete retained terminal execution events")
    parser.add_argument("--days", type=int, default=settings.execution_event_retention_days)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    result = cleanup_execution_events(args.days, args.limit)
    print(
        f"execution event cleanup complete: executions={result.executions} events={result.events}"
    )


if __name__ == "__main__":
    main()
