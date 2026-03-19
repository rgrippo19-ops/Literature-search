from __future__ import annotations

from .config import SETTINGS
from .graph import build_graph
from .schemas import AnalyzeResponse, Citation


def clamp_request(
    *,
    question: str,
    max_papers: int | None,
    search_years: int | None,
    full_text: bool | None,
):
    question = question.strip()
    if not question:
        raise ValueError("Question is required.")

    if len(question) > SETTINGS.max_question_length:
        raise ValueError(
            f"Question exceeds MAX_QUESTION_LENGTH ({SETTINGS.max_question_length})."
        )

    max_papers_used = min(
        max_papers or SETTINGS.default_max_papers,
        SETTINGS.max_allowed_papers,
    )

    search_years_used = min(
        search_years or SETTINGS.default_search_years,
        SETTINGS.max_allowed_search_years,
    )

    full_text_used = bool(full_text) and SETTINGS.allow_fulltext

    return question, max_papers_used, search_years_used, full_text_used


def run_pipeline(
    *,
    question: str,
    max_papers: int | None,
    search_years: int | None,
    full_text: bool | None,
) -> AnalyzeResponse:
    question, max_papers_used, search_years_used, full_text_used = clamp_request(
        question=question,
        max_papers=max_papers,
        search_years=search_years,
        full_text=full_text,
    )

    app = build_graph()

    result = app.invoke(
        {
            "user_question": question,
            "reasoning_chain": [],
            "failure_flags": [],
            "telemetry": {},
            "runtime_max_papers": max_papers_used,
            "runtime_search_years": search_years_used,
            "runtime_full_text": full_text_used,
        }
    )

    citations = []
    for c in result.get("citations", []):
        if hasattr(c, "title"):
            citations.append(
                Citation(
                    title=c.title,
                    year=c.year,
                    url=getattr(c, "source_url", "") or getattr(c, "url", ""),
                )
            )
        else:
            citations.append(
                Citation(
                    title=c.get("title", "Untitled"),
                    year=c.get("year", 0),
                    url=c.get("source_url", "") or c.get("url", ""),
                )
            )

    return AnalyzeResponse(
        question=question,
        normalized_question=result.get("normalized_question", question),
        max_papers_used=max_papers_used,
        search_years_used=search_years_used,
        full_text_used=full_text_used,
        answer=result.get("final_answer", ""),
        citations=citations,
        debug=result.get("telemetry", {}),
    )