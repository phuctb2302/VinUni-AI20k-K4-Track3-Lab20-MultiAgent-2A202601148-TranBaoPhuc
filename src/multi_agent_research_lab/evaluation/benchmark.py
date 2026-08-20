import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, estimated cost, quality score, citation coverage, and failure rate."""
    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    # 1. Total estimated cost
    total_cost = sum(r.metadata.get("cost_usd", 0.0) or 0.0 for r in state.agent_results)

    # 2. Citation coverage
    final_text = state.final_answer or ""
    citations_found = re.findall(r"\[(?:Source\s*)?\d+\]", final_text, re.IGNORECASE)
    sources_count = len(state.sources)
    citation_coverage = (
        min(1.0, len(citations_found) / max(1, sources_count))
        if sources_count > 0
        else (0.0 if not citations_found else 1.0)
    )

    # 3. Quality score (heuristic based on structural completeness, citations, and content length)
    quality = 5.0
    if len(final_text) > 400:
        quality += 1.5
    if "## References" in final_text or "## Sources" in final_text:
        quality += 1.0
    if citation_coverage >= 0.5:
        quality += 1.5
    if state.analysis_notes and len(state.analysis_notes) > 100:
        quality += 1.0
    quality = min(10.0, max(0.0, quality))

    # 4. Failure rate
    failure_rate = 1.0 if (not state.final_answer or state.errors) else 0.0

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=total_cost if total_cost > 0 else None,
        quality_score=quality,
        citation_coverage=citation_coverage,
        failure_rate=failure_rate,
        notes=f"Routes: {len(state.route_history)} steps, {len(state.sources)} sources",
    )
    return state, metrics
