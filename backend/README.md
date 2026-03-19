# Backend

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e .
copy .env.example .env
uvicorn biomed_multi_agent.api:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints
- `GET /health`
- `GET /settings`
- `POST /analyze`
