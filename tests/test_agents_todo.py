"""Unit tests for SupervisorAgent and MultiAgentWorkflow."""

from multi_agent_research_lab.agents import (
    SupervisorAgent,
)
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_supervisor_routes_to_researcher_when_empty() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    supervisor = SupervisorAgent()
    updated = supervisor.run(state)
    assert updated.route_history == ["researcher"]
    assert updated.iteration == 1


def test_supervisor_routes_to_analyst_after_research() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "Found some papers on agents"
    state.sources = []
    # If no sources, still needs researcher
    supervisor = SupervisorAgent()
    updated = supervisor.run(state)
    assert updated.route_history[-1] == "researcher"

    # With sources and research notes -> analyst
    state.sources = [
        type("Doc", (), {"title": "Paper 1", "snippet": "Text", "url": None, "metadata": {}})()
    ]  # type: ignore
    state2 = supervisor.run(state)
    assert state2.route_history[-1] == "analyst"


def test_multi_agent_workflow_completes_end_to_end() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent architectures"))
    workflow = MultiAgentWorkflow()
    final_state = workflow.run(state)

    assert len(final_state.sources) > 0
    assert final_state.research_notes is not None
    assert final_state.analysis_notes is not None
    assert final_state.final_answer is not None
    assert "writer" in final_state.route_history
