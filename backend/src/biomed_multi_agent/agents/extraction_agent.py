from __future__ import annotations

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import EXTRACTION_PROMPT
from ..schemas import FindingRecord
from ..state import WorkflowState


def extraction_agent(state: WorkflowState) -> WorkflowState:
    findings: list[FindingRecord] = []
    question = state["normalized_question"]
    for idx, paper in enumerate(state.get("selected_papers", []), start=1):
        text = _paper_context(paper)
        user_prompt = (
            f"User question: {question}\n\n"
            f"Paper metadata:\n"
            f"PMID: {paper.pmid}\n"
            f"PMCID: {paper.pmcid}\n"
            f"Title: {paper.title}\n"
            f"Year: {paper.year}\n"
            f"Journal: {paper.journal}\n"
            f"Publication types: {', '.join(paper.publication_types)}\n"
            f"Species hint: {paper.species_hint}\n"
            f"Evidence source type: {paper.evidence_source_type}\n\n"
            f"Article text:\n{text}\n\n"
            f"Return one structured finding with claim_id F{idx} and paper_id {paper.paper_id}."
        )
        result = LLM.generate_model(
            model=SETTINGS.extraction_model,
            system_prompt=EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            schema_model=FindingRecord,
        )
        findings.append(result)
    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Extraction agent created {len(findings)} structured finding records using {SETTINGS.extraction_model}.")
    return {**state, "extraction_records": findings, "reasoning_chain": reasoning}


def _paper_context(paper) -> str:
    parts = []
    if paper.abstract:
        parts.append("ABSTRACT:\n" + paper.abstract)
    if paper.full_text:
        parts.append("FULL TEXT EXCERPT:\n" + paper.full_text)
    return "\n\n".join(parts)[:20000]
