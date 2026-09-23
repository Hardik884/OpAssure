"""Create or reset the database schema — no manual SQL needed.

    python -m app.db.init_db           # create any missing tables
    python -m app.db.init_db --reset   # drop every OpAssure table, then recreate (empty)

The schema is defined by the ORM models in app/models/ (see migrations/README.md).
"""

import argparse

from sqlalchemy import Engine

from app.db.session import get_engine
from app.models import Base


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def reset_schema(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="drop and recreate all tables")
    args = parser.parse_args()

    engine = get_engine()
    if args.reset:
        reset_schema(engine)
        print(f"Reset schema: {len(Base.metadata.tables)} tables recreated (empty).")
    else:
        create_schema(engine)
        print(f"Schema ready: {', '.join(sorted(Base.metadata.tables))}")


if __name__ == "__main__":
    main()
