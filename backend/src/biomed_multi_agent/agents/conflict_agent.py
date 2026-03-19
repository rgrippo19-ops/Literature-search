from __future__ import annotations

from itertools import combinations

from pydantic import BaseModel

from ..config import SETTINGS
from ..llm import LLM
from ..prompts import CONFLICT_PROMPT
from ..schemas import ConflictRecord, FindingRecord
from ..state import WorkflowState


class ConflictDecision(BaseModel):
    conflict_id: str
    claim_a_id: str
    claim_b_id: str
    conflict_type: str
    explanation: str
    severity: str


VALID_TYPES = {"direct", "species_mismatch", "method_mismatch", "outcome_mismatch", "interpretation_mismatch"}
VALID_SEVERITIES = {"low", "medium", "high"}


def conflict_agent(state: WorkflowState) -> WorkflowState:
    findings = state.get("extraction_records", [])
    methods = {m.paper_id: m for m in state.get("method_records", [])}
    conflicts: list[ConflictRecord] = []
    for idx, (a, b) in enumerate(combinations(findings, 2), start=1):
        if not _likely_related(a, b):
            continue
        method_a = methods.get(a.paper_id)
        method_b = methods.get(b.paper_id)
        user_prompt = (
            f"Finding A:\n{a.model_dump_json(indent=2)}\n\n"
            f"Method A:\n{method_a.model_dump_json(indent=2) if method_a else '{}'}\n\n"
            f"Finding B:\n{b.model_dump_json(indent=2)}\n\n"
            f"Method B:\n{method_b.model_dump_json(indent=2) if method_b else '{}'}\n\n"
            f"Return conflict_id C{idx}. If there is no material conflict, prefer interpretation_mismatch with low severity and explain why."
        )
        decision = LLM.generate_model(
            model=SETTINGS.extraction_model,
            system_prompt=CONFLICT_PROMPT,
            user_prompt=user_prompt,
            schema_model=ConflictDecision,
        )
        if decision.conflict_type not in VALID_TYPES or decision.severity not in VALID_SEVERITIES:
            continue
        conflicts.append(ConflictRecord(**decision.model_dump()))
    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Conflict agent found {len(conflicts)} potential conflicts or mismatches.")
    return {**state, "conflict_records": conflicts, "reasoning_chain": reasoning}


def _likely_related(a: FindingRecord, b: FindingRecord) -> bool:
    text = f"{a.outcome} {a.intervention_or_context} {b.outcome} {b.intervention_or_context}".lower()
    return "circadian" in text or "entrain" in text or "dopamine" in text
