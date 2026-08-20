import logging
from typing import Any

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph with LangGraph."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.supervisor = SupervisorAgent()
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self.app: Any = None

    def build(self) -> Any:
        """Create and compile a LangGraph StateGraph."""
        try:
            from langgraph.graph import END, StateGraph

            builder = StateGraph(ResearchState)

            # Define node wrappers
            builder.add_node("supervisor", lambda s: self.supervisor.run(s))
            builder.add_node("researcher", lambda s: self.researcher.run(s))
            builder.add_node("analyst", lambda s: self.analyst.run(s))
            builder.add_node("writer", lambda s: self.writer.run(s))

            builder.set_entry_point("supervisor")

            # Conditional routing edge out of supervisor
            def route_edge(state: ResearchState) -> str:
                if state.route_history:
                    last_route = state.route_history[-1]
                    if last_route in ["researcher", "analyst", "writer"]:
                        return last_route
                return END

            builder.add_conditional_edges(
                "supervisor",
                route_edge,
                {
                    "researcher": "researcher",
                    "analyst": "analyst",
                    "writer": "writer",
                    END: END,
                },
            )

            # Return edges back to supervisor (centralized orchestration)
            builder.add_edge("researcher", "supervisor")
            builder.add_edge("analyst", "supervisor")
            builder.add_edge("writer", "supervisor")

            self.app = builder.compile()
            return self.app
        except Exception as exc:
            logger.debug(
                f"LangGraph initialization bypassed ({exc}). Using native state machine runner."
            )
            self.app = None
            return None

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return the final state."""
        if self.app is None:
            self.build()

        if self.app is not None:
            try:
                # Invoke compiled LangGraph
                output = self.app.invoke(state)
                if isinstance(output, ResearchState):
                    return output
                if isinstance(output, dict):
                    return ResearchState.model_validate(output)
            except Exception as e:
                logger.warning(
                    f"LangGraph execution exception ({e}), falling back to direct orchestration."
                )

        # Robust direct fallback execution loop
        current_state = state
        while current_state.iteration < self.settings.max_iterations:
            current_state = self.supervisor.run(current_state)
            if not current_state.route_history:
                break

            last_route = current_state.route_history[-1]
            if last_route == "researcher":
                current_state = self.researcher.run(current_state)
            elif last_route == "analyst":
                current_state = self.analyst.run(current_state)
            elif last_route == "writer":
                current_state = self.writer.run(current_state)
            elif last_route == "done":
                break
            else:
                logger.warning(f"Unknown route '{last_route}'. Stopping workflow.")
                break

        return current_state
