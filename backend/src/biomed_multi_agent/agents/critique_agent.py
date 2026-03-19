from __future__ import annotations

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import CRITIQUE_PROMPT
from ..schemas import CritiqueRecord
from ..state import WorkflowState


def critique_agent(state: WorkflowState) -> WorkflowState:
    critiques: list[CritiqueRecord] = []
    question = state["normalized_question"]
    for paper in state.get("selected_papers", []):
        text = _paper_context(paper)
        user_prompt = (
            f"Question: {question}\n\n"
            f"Paper metadata:\n"
            f"PMID: {paper.pmid}\n"
            f"Title: {paper.title}\n"
            f"Year: {paper.year}\n"
            f"Publication types: {', '.join(paper.publication_types)}\n"
            f"Species hint: {paper.species_hint}\n"
            f"Evidence source type: {paper.evidence_source_type}\n\n"
            f"Article text:\n{text}\n\n"
            f"Return a critique record for paper_id {paper.paper_id}."
        )
        result = LLM.generate_model(
            model=SETTINGS.extraction_model,
            system_prompt=CRITIQUE_PROMPT,
            user_prompt=user_prompt,
            schema_model=CritiqueRecord,
        )
        critiques.append(result)
    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Critique agent produced {len(critiques)} critique records.")
    return {**state, "critique_records": critiques, "reasoning_chain": reasoning}


def _paper_context(paper) -> str:
    parts = []
    if paper.abstract:
        parts.append("ABSTRACT:\n" + paper.abstract)
    if paper.full_text:
        parts.append("FULL TEXT EXCERPT:\n" + paper.full_text)
    return "\n\n".join(parts)[:16000]
