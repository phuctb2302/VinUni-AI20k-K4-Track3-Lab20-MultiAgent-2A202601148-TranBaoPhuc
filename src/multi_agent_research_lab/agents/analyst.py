import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self) -> None:
        self.llm_client = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""
        logger.info(f"AnalystAgent analyzing research notes for: {state.request.query}")

        research_notes = state.research_notes or "No research notes provided."
        system_prompt = (
            "You are a Critical Systems Analyst. Your goal is to critically evaluate "
            "raw research findings, highlight trade-offs, identify strengths and limitations, "
            "compare alternative approaches, and identify conflicting evidence or missing gaps."
        )
        user_prompt = (
            f"Original Query: {state.request.query}\n\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
            "Produce structured analysis notes with:\n"
            "1. Key Insights & Core Principles\n"
            "2. Trade-offs (Performance vs Complexity vs Cost)\n"
            "3. Critical Comparison & Edge Cases\n"
            "4. Practical Recommendations"
        )

        response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        state.analysis_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "analyst_completed",
            {
                "analysis_length": len(state.analysis_notes),
            },
        )
        return state
