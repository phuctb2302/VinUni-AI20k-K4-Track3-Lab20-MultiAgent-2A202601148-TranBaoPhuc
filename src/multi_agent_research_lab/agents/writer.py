import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self) -> None:
        self.llm_client = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""
        logger.info(f"WriterAgent composing final report for: {state.request.query}")

        sources_ref = []
        for idx, s in enumerate(state.sources, start=1):
            sources_ref.append(f"[{idx}] {s.title} ({s.url or 'N/A'})")
        sources_list_str = "\n".join(sources_ref)

        system_prompt = (
            "You are a Principal Technical Writer and Research Author. Your task is to craft an "
            "authoritative, comprehensive final research report based strictly on the provided "
            "research notes, analysis notes, and source materials.\n"
            "Requirements:\n"
            "- Use clear markdown formatting (Headings, Bullet points, Architecture blocks).\n"
            "- Strictly ground assertions using citations like [Source 1], [Source 2].\n"
            "- Include Executive Summary, Key Findings, Comparative Analysis, Practical "
            "Guidelines, and a References section at the end."
        )

        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Target Audience: {state.request.audience}\n\n"
            f"Available Sources:\n{sources_list_str}\n\n"
            f"Research Notes:\n{state.research_notes or 'N/A'}\n\n"
            f"Analysis Notes:\n{state.analysis_notes or 'N/A'}\n\n"
            "Write the comprehensive final research report."
        )

        response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        final_answer = response.content

        # Append reference list if not already present
        if sources_ref and "## References" not in final_answer:
            final_answer += "\n\n## References\n" + "\n".join(
                [
                    f"- **[Source {idx}]**: {s.title} - {s.url or 'Offline Corpus'}"
                    for idx, s in enumerate(state.sources, start=1)
                ]
            )

        state.final_answer = final_answer

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "writer_completed",
            {
                "final_answer_length": len(state.final_answer),
            },
        )
        return state
