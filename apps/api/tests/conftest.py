import os


os.environ["DATABASE_URL"] = "sqlite+pysqlite:////tmp/cfo_orchestrator_tests.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["NETSUITE_MODE"] = "mock"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5-coder:7b"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"


def pytest_sessionstart(session) -> None:
    import os as _os

    from app.core.config import get_settings
    from app.core.database import init_db

    db_path = "/tmp/cfo_orchestrator_tests.db"
    if _os.path.exists(db_path):
        _os.remove(db_path)

    get_settings.cache_clear()
    init_db()
