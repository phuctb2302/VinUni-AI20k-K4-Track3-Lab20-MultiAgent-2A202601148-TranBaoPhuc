import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self) -> None:
        self.settings = get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""
        # 1. Guardrail: Max iterations check to prevent infinite loops
        if state.iteration >= self.settings.max_iterations:
            next_route = "done"
            logger.warning(
                f"Supervisor reached max iterations ({self.settings.max_iterations}). Forcing STOP."
            )
            state.errors.append("Supervisor hit max_iterations limit.")
            state.record_route(next_route)
            state.add_trace_event(
                "supervisor_route", {"next": next_route, "reason": "max_iterations_reached"}
            )
            return state

        # 2. State-based routing policy
        if not state.sources or not state.research_notes:
            next_route = "researcher"
        elif not state.analysis_notes:
            next_route = "analyst"
        elif not state.final_answer:
            next_route = "writer"
        else:
            next_route = "done"

        state.record_route(next_route)
        state.add_trace_event(
            "supervisor_route",
            {
                "iteration": state.iteration,
                "next": next_route,
                "has_sources": bool(state.sources),
                "has_research": bool(state.research_notes),
                "has_analysis": bool(state.analysis_notes),
                "has_final": bool(state.final_answer),
            },
        )
        return state
