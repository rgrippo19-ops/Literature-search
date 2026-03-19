from __future__ import annotations

from pydantic import BaseModel

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import SYNTHESIS_PROMPT
from ..state import WorkflowState


class SynthesisOutput(BaseModel):
    final_answer: str


def synthesis_agent(state: WorkflowState) -> WorkflowState:
    """
    Final writing step.

    This agent should:
    - answer the user's actual question
    - use only the structured intermediate records
    - avoid forcing a rigid report template
    - produce a thorough scientific narrative
    - end with a short 'Follow-up questions' section
    """

    payload = {
        "question": state["normalized_question"],
        "findings": [f.model_dump() for f in state.get("extraction_records", [])],
        "methods": [m.model_dump() for m in state.get("method_records", [])],
        "critiques": [c.model_dump() for c in state.get("critique_records", [])],
        "conflicts": [c.model_dump() for c in state.get("conflict_records", [])],
        "papers": [
            {
                "paper_id": p.paper_id,
                "pmid": p.pmid,
                "pmcid": p.pmcid,
                "title": p.title,
                "year": p.year,
                "journal": p.journal,
                "source_url": p.source_url,
                "evidence_source_type": p.evidence_source_type,
                "species_hint": p.species_hint,
                "publication_types": p.publication_types,
            }
            for p in state.get("selected_papers", [])
        ],
    }

    user_prompt = (
        f"User question: {state['normalized_question']}\n\n"
        "Use only the structured records below. Write a thorough, question-driven scientific synthesis in mostly continuous prose. "
        "Do not force a standard review template or fixed section headings. "
        "Organize the answer around the logic of the user's question and the actual evidence provided. "
        "Integrate the cited literature naturally, distinguish what is well supported from what is uncertain, "
        "and mention limitations or disagreements only where they matter for interpretation. "
        "End with a section titled 'Follow-up questions' containing 3 strong research questions.\n\n"
        f"{payload}"
    )

    result = LLM.generate_model(
        model=SETTINGS.synthesis_model,
        system_prompt=SYNTHESIS_PROMPT,
        user_prompt=user_prompt,
        schema_model=SynthesisOutput,
    )

    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(
        f"Synthesis agent drafted the final answer using {SETTINGS.synthesis_model}."
    )

    return {
        **state,
        "final_answer": result.final_answer,
        "reasoning_chain": reasoning,
    }