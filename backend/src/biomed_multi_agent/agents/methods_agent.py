from __future__ import annotations

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import METHODS_PROMPT
from ..schemas import MethodRecord
from ..state import WorkflowState


def methods_agent(state: WorkflowState) -> WorkflowState:
    methods: list[MethodRecord] = []
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
            f"Species hint: {paper.species_hint}\n\n"
            f"Article text:\n{text}\n\n"
            f"Return a method summary for paper_id {paper.paper_id}."
        )
        result = LLM.generate_model(
            model=SETTINGS.extraction_model,
            system_prompt=METHODS_PROMPT,
            user_prompt=user_prompt,
            schema_model=MethodRecord,
        )
        methods.append(result)
    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Methods agent created {len(methods)} method records.")
    return {**state, "method_records": methods, "reasoning_chain": reasoning}


def _paper_context(paper) -> str:
    parts = []
    if paper.abstract:
        parts.append("ABSTRACT:\n" + paper.abstract)
    if paper.full_text:
        parts.append("FULL TEXT EXCERPT:\n" + paper.full_text)
    return "\n\n".join(parts)[:16000]
