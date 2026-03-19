from __future__ import annotations

import time

from ..config import SETTINGS
from ..state import WorkflowState
from ..tools.ncbi import search_pubmed


def search_agent(state: WorkflowState) -> WorkflowState:
    queries = state.get('search_queries', [])
    start = time.perf_counter()
    max_papers = state.get('runtime_max_papers') or SETTINGS.max_papers
    papers = search_pubmed(queries, max_papers=max_papers, max_papers_per_query=SETTINGS.max_papers_per_query)
    reasoning = list(state.get('reasoning_chain', []))
    reasoning.append(f'Search agent retrieved {len(papers)} papers from PubMed/PMC in {time.perf_counter() - start:.2f}s.')
    telemetry = dict(state.get('telemetry', {}))
    telemetry['retrieved_papers'] = len(papers)
    return {
        **state,
        'candidate_papers': papers,
        'selected_papers': papers,
        'reasoning_chain': reasoning,
        'telemetry': telemetry,
    }
