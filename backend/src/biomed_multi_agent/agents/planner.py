from __future__ import annotations

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import PLANNER_PROMPT
from ..schemas import SearchPlan
from ..state import WorkflowState


def planner_agent(state: WorkflowState) -> WorkflowState:
    question = state["user_question"]
    prompt = (
        "Normalize this biomedical literature question and propose precise PubMed search queries. "
        "Prefer current terminology, include likely synonyms, and separate species when useful.\n\n"
        f"Question: {question}"
    )
    plan = LLM.generate_model(
        model=SETTINGS.planner_model,
        system_prompt=PLANNER_PROMPT,
        user_prompt=prompt,
        schema_model=SearchPlan,
    )
    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Planner generated {len(plan.search_queries)} PubMed queries.")
    return {
        **state,
        "normalized_question": plan.normalized_question,
        "search_queries": plan.search_queries,
        "reasoning_chain": reasoning,
    }
