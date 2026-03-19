from __future__ import annotations

from langgraph.graph import END, StateGraph

from .agents.citation_agent import citation_agent
from .agents.conflict_agent import conflict_agent
from .agents.critique_agent import critique_agent
from .agents.extraction_agent import extraction_agent
from .agents.methods_agent import methods_agent
from .agents.planner import planner_agent
from .agents.search_agent import search_agent
from .agents.synthesis_agent import synthesis_agent
from .state import WorkflowState


def build_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node('plan', planner_agent)
    workflow.add_node('search', search_agent)
    workflow.add_node('extract', extraction_agent)
    workflow.add_node('methods', methods_agent)
    workflow.add_node('critique', critique_agent)
    workflow.add_node('conflict', conflict_agent)
    workflow.add_node('synthesize', synthesis_agent)
    workflow.add_node('cite', citation_agent)

    workflow.set_entry_point('plan')
    workflow.add_edge('plan', 'search')
    workflow.add_edge('search', 'extract')
    workflow.add_edge('extract', 'methods')
    workflow.add_edge('methods', 'critique')
    workflow.add_edge('critique', 'conflict')
    workflow.add_edge('conflict', 'synthesize')
    workflow.add_edge('synthesize', 'cite')
    workflow.add_edge('cite', END)
    return workflow.compile()
