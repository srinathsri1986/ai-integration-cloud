import os


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:////private/tmp/cfo_orchestrator_tests.db")


def pytest_sessionstart(session) -> None:
    from app.core.database import init_db

    init_db()
