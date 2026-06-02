import os


os.environ["DATABASE_URL"] = "sqlite+pysqlite:////private/tmp/cfo_orchestrator_tests.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["NETSUITE_MODE"] = "mock"
os.environ["OPENAI_API_KEY"] = ""
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen2.5-coder:7b"


def pytest_sessionstart(session) -> None:
    from app.core.config import get_settings
    from app.core.database import init_db

    get_settings.cache_clear()
    init_db()
