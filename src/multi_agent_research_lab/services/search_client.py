import json
import logging
from pathlib import Path

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client supporting Tavily API and local offline corpus."""

    def __init__(self, api_key: str | None = None) -> None:
        self.settings = get_settings()
        self.api_key = api_key or self.settings.tavily_api_key
        self.corpus_dir = Path("ai_agent_offline_research_corpus_v2/topics")

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""
        if self.api_key and self.api_key.strip():
            try:
                return self._search_tavily(query, max_results)
            except Exception as e:
                logger.warning(f"Tavily search failed ({e}), falling back to local corpus search.")

        return self._search_local_corpus(query, max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        """Query Tavily Search API."""
        import ssl
        import urllib.request

        import certifi

        url = "https://api.tavily.com/search"
        payload = json.dumps(
            {"api_key": self.api_key, "query": query, "max_results": max_results}
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "MultiAgentResearchLab/1.0"},
        )
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=10, context=context) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results: list[SourceDocument] = []
        for item in data.get("results", []):
            results.append(
                SourceDocument(
                    title=item.get("title", "Untitled Source"),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    metadata={"score": item.get("score")},
                )
            )
        return results

    def _search_local_corpus(self, query: str, max_results: int) -> list[SourceDocument]:
        """Search in local JSON topic corpus if available, else return mock sources."""
        query_words = set(query.lower().replace("-", " ").replace("_", " ").split())
        results: list[SourceDocument] = []

        if self.corpus_dir.exists():
            # Find best matching topic file
            topic_files = list(self.corpus_dir.glob("*.json"))
            best_match_file = None
            best_score = -1

            for tf in topic_files:
                name_words = set(tf.stem.lower().replace("_", " ").split())
                score = len(query_words.intersection(name_words))
                if score > best_score:
                    best_score = score
                    best_match_file = tf

            target_file = (
                best_match_file
                if (best_match_file and best_score > 0)
                else (topic_files[0] if topic_files else None)
            )

            if target_file:
                try:
                    with open(target_file, encoding="utf-8") as f:
                        topic_data = json.load(f)
                    kb = topic_data.get("knowledge_base", {})
                    source_docs = kb.get("source_documents", [])
                    articles = kb.get("knowledge_articles", [])

                    for doc in source_docs[:max_results]:
                        results.append(
                            SourceDocument(
                                title=doc.get("title", "Corpus Document"),
                                url=doc.get("url") or f"offline://corpus/{doc.get('id', 'doc')}",
                                snippet=doc.get("summary")
                                or doc.get("snippet")
                                or str(doc.get("key_points", "")),
                                metadata={
                                    "source_id": doc.get("id"),
                                    "corpus_topic": topic_data.get("topic", ""),
                                },
                            )
                        )

                    if len(results) < max_results:
                        for art in articles[: max_results - len(results)]:
                            results.append(
                                SourceDocument(
                                    title=art.get("title", "Corpus Article"),
                                    url=f"offline://corpus/{art.get('id', 'article')}",
                                    snippet=art.get("abstract") or art.get("content", "")[:300],
                                    metadata={"article_id": art.get("id")},
                                )
                            )
                except Exception as e:
                    logger.warning(f"Error reading corpus topic: {e}")

        if not results:
            # Fallback mock sources
            results = [
                SourceDocument(
                    title="Anthropic: Building Effective Agents",
                    url="https://www.anthropic.com/engineering/building-effective-agents",
                    snippet=(
                        "Architectural patterns for autonomous agents including routing, "
                        "supervisor patterns, and handoffs."
                    ),
                    metadata={"source_id": "SRC-001"},
                ),
                SourceDocument(
                    title="LangGraph: Multi-Agent Orchestration Framework",
                    url="https://langchain-ai.github.io/langgraph/concepts/",
                    snippet=(
                        "Cyclic graph orchestration with explicit state management, "
                        "human-in-the-loop, and persistence."
                    ),
                    metadata={"source_id": "SRC-002"},
                ),
                SourceDocument(
                    title="Production Guardrails for AI Workflows",
                    url="https://arxiv.org/abs/2401.00000",
                    snippet=(
                        "Techniques for bounded execution, timeout controls, and "
                        "preventing infinite routing loops in agent teams."
                    ),
                    metadata={"source_id": "SRC-003"},
                ),
            ]

        return results[:max_results]
