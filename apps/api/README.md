# API

FastAPI service for CFO intelligence endpoints. The first connector mode is `mock`, using named NetSuite query templates only.

## Local development

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```

## Safety model

- No real NetSuite credentials are used.
- No arbitrary SQL or SuiteQL endpoint is exposed.
- Connector access goes through approved template IDs in `app/connectors/netsuite/query_templates.py`.
