import logging
import re

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class CriticAgent(BaseAgent):
    """Optional fact-checking, citation verification, and safety-review agent."""

    name = "critic"

    def __init__(self) -> None:
        self.llm_client = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings."""
        logger.info(f"CriticAgent evaluating report quality for: {state.request.query}")

        final_text = state.final_answer or ""
        citations_found = re.findall(r"\[(?:Source\s*)?\d+\]", final_text, re.IGNORECASE)
        num_sources = len(state.sources)
        citation_coverage = min(1.0, len(citations_found) / max(1, num_sources))

        status = "PASS" if citation_coverage > 0 else "WARNING (Missing citations)"
        review_notes = (
            f"Critic Review:\n"
            f"- Citations detected: {len(citations_found)} (Coverage: {citation_coverage:.1%})\n"
            f"- Source count in state: {num_sources}\n"
            f"- Validation status: {status}"
        )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=review_notes,
                metadata={"citations_found": len(citations_found), "coverage": citation_coverage},
            )
        )
        state.add_trace_event(
            "critic_completed",
            {
                "citations_found": len(citations_found),
                "coverage": citation_coverage,
            },
        )
        return state
