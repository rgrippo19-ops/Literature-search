from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

# -----------------------------
# Public API schemas
# -----------------------------

class AnalyzeRequest(BaseModel):
    question: str
    max_papers: int | None = None
    search_years: int | None = None
    full_text: bool | None = None


class Citation(BaseModel):
    title: str
    year: int
    url: str


class AnalyzeResponse(BaseModel):
    question: str
    normalized_question: str
    max_papers_used: int
    search_years_used: int
    full_text_used: bool
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    debug: dict = Field(default_factory=dict)


class PublicSettings(BaseModel):
    default_max_papers: int
    max_allowed_papers: int
    default_search_years: int
    max_allowed_search_years: int
    allow_fulltext: bool
    max_question_length: int


# -----------------------------
# Internal production pipeline schemas
# -----------------------------

Species = Literal["human", "mouse", "rat", "rodent", "mixed", "unknown"]
Direction = Literal["supports", "mixed", "null", "contradicts"]
EvidenceSourceType = Literal["abstract", "full_text", "mixed"]
ConflictType = Literal[
    "direct",
    "species_mismatch",
    "method_mismatch",
    "outcome_mismatch",
    "interpretation_mismatch",
]


class SearchPlan(BaseModel):
    normalized_question: str
    search_queries: list[str] = Field(default_factory=list)
    inclusion_notes: list[str] = Field(default_factory=list)
    exclusion_notes: list[str] = Field(default_factory=list)


class PaperRecord(BaseModel):
    paper_id: str
    pmid: str = ""
    pmcid: str = ""
    doi: str = ""
    title: str
    year: int
    journal: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    full_text: str = ""
    evidence_source_type: EvidenceSourceType = "abstract"
    species_hint: Species = "unknown"
    publication_types: list[str] = Field(default_factory=list)
    source_url: str
    selection_reason: str = ""


class FindingRecord(BaseModel):
    paper_id: str
    claim_id: str
    claim_text: str
    evidence_span: str
    species: Species = "unknown"
    intervention_or_context: str = ""
    outcome: str = ""
    direction: Direction = "mixed"
    confidence: float = 0.0
    evidence_source_type: EvidenceSourceType = "abstract"


class MethodRecord(BaseModel):
    paper_id: str
    study_type: str
    sample_description: str = ""
    sample_size: str = ""
    assay_or_measure: str = ""
    design_notes: str = ""


class CritiqueRecord(BaseModel):
    paper_id: str
    limitations: list[str] = Field(default_factory=list)
    confounds: list[str] = Field(default_factory=list)
    overclaim_risk: Literal["low", "medium", "high"] = "low"


class ConflictRecord(BaseModel):
    conflict_id: str
    claim_a_id: str
    claim_b_id: str
    conflict_type: ConflictType
    explanation: str
    severity: Literal["low", "medium", "high"]


class CitationRecord(BaseModel):
    claim_label: str
    paper_id: str
    pmid: str = ""
    pmcid: str = ""
    title: str
    year: int
    source_url: str


class RunOutput(BaseModel):
    question: str
    normalized_question: str
    final_answer: str
    citations: list[CitationRecord]
    findings: list[FindingRecord]
    methods: list[MethodRecord]
    critiques: list[CritiqueRecord]
    conflicts: list[ConflictRecord]
    reasoning_chain: list[str]
    telemetry: dict = Field(default_factory=dict)