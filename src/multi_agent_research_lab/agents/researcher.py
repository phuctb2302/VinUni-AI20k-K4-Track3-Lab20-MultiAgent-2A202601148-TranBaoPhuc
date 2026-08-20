import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self) -> None:
        self.search_client = SearchClient()
        self.llm_client = LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        query = state.request.query
        logger.info(f"ResearcherAgent gathering evidence for query: {query}")

        # 1. Gather sources
        sources = self.search_client.search(query, max_results=state.request.max_sources)
        state.sources = sources

        # 2. Prepare context for synthesis
        source_texts = []
        for idx, doc in enumerate(sources, start=1):
            source_texts.append(
                f"[Source {idx}] {doc.title}\nURL/ID: {doc.url}\nContent: {doc.snippet}"
            )
        context_str = "\n\n".join(source_texts)

        system_prompt = (
            "You are a meticulous Senior Research Scientist. Your job is to extract, summarize, "
            "and organize factual findings from provided sources into concise research notes. "
            "Always reference which source ([Source 1], [Source 2], etc.) supports each point."
        )
        user_prompt = (
            f"Research Question: {query}\n\n"
            f"Evidence Documents:\n{context_str}\n\n"
            "Please generate structured research notes with key facts, definitions, and mechanisms."
        )

        # 3. Generate research notes via LLM
        response = self.llm_client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        state.research_notes = response.content

        # 4. Record agent result and trace
        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={
                    "sources_count": len(sources),
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "researcher_completed",
            {
                "sources_gathered": len(sources),
                "notes_length": len(state.research_notes),
            },
        )
        return state
