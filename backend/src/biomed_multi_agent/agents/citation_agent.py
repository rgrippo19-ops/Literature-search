from __future__ import annotations

from ..schemas import CitationRecord
from ..state import WorkflowState


def citation_agent(state: WorkflowState) -> WorkflowState:
    citations: list[CitationRecord] = []
    seen: set[str] = set()
    for paper in state.get('selected_papers', []):
        key = paper.pmid or paper.pmcid or paper.paper_id
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            CitationRecord(
                claim_label=f'Source-{len(citations) + 1}',
                paper_id=paper.paper_id,
                pmid=paper.pmid,
                pmcid=paper.pmcid,
                title=paper.title,
                year=paper.year,
                source_url=paper.source_url,
            )
        )
    reasoning = list(state.get('reasoning_chain', []))
    reasoning.append(f'Citation agent attached {len(citations)} citation records.')
    return {**state, 'citations': citations, 'reasoning_chain': reasoning}
