from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import SETTINGS
from .pipeline import run_pipeline
from .schemas import AnalyzeRequest, AnalyzeResponse, PublicSettings

app = FastAPI(title="Biomedical Public App API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    return {"ok": True}

@app.get("/settings", response_model=PublicSettings)
def settings() -> PublicSettings:
    return PublicSettings(
        default_max_papers=SETTINGS.default_max_papers,
        max_allowed_papers=SETTINGS.max_allowed_papers,
        default_search_years=SETTINGS.default_search_years,
        max_allowed_search_years=SETTINGS.max_allowed_search_years,
        allow_fulltext=SETTINGS.allow_fulltext,
        max_question_length=SETTINGS.max_question_length,
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return run_pipeline(
            question=payload.question,
            max_papers=payload.max_papers,
            search_years=payload.search_years,
            full_text=payload.full_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}") from exc
