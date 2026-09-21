import argparse

from app.core.config import get_settings
from app.core.database import new_session
from app.services.query_service import QueryService


def recover(limit: int) -> tuple[int, int]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    settings = get_settings()
    with new_session() as db:
        return QueryService(db, settings).recover_available(limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Recover stale Text2SQL executions")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    discovered, claimed = recover(args.limit)
    print(f"recovery scan complete: discovered={discovered} claimed={claimed}")


if __name__ == "__main__":
    main()
