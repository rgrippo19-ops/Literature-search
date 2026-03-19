from __future__ import annotations

from typing import Any, Optional, TypedDict
from typing_extensions import Annotated

from .schemas import CitationRecord, ConflictRecord, CritiqueRecord, FindingRecord, MethodRecord, PaperRecord


class WorkflowState(TypedDict, total=False):
    user_question: str
    normalized_question: str
    search_queries: list[str]
    candidate_papers: list[PaperRecord]
    selected_papers: list[PaperRecord]
    extraction_records: list[FindingRecord]
    method_records: list[MethodRecord]
    critique_records: list[CritiqueRecord]
    conflict_records: list[ConflictRecord]
    citations: list[CitationRecord]
    final_answer: str
    failure_flags: list[str]
    reasoning_chain: Annotated[list[str], "append"]
    telemetry: dict[str, Any]
    output_path: Optional[str]
    runtime_max_papers: Optional[int]
