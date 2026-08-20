"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to a rich markdown report with trade-off analysis."""

    lines = [
        "# Benchmark Report: Single-Agent Baseline vs Multi-Agent Research System",
        "",
        "## 1. Quantitative Comparison",
        "",
        "| Run | Latency | Cost (USD) | Quality | Citations | Fail Rate | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "N/A" if item.estimated_cost_usd is None else f"${item.estimated_cost_usd:.5f}"
        quality = "N/A" if item.quality_score is None else f"{item.quality_score:.1f}/10"
        citation = "N/A" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "0%" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        lines.append(
            f"| **{item.run_name}** | {item.latency_seconds:.2f}s | {cost} | {quality} "
            f"| {citation} | {failure} | {item.notes} |"
        )

    lines.extend(
        [
            "",
            "## 2. Key Findings & Trade-off Analysis",
            "",
            "- **Specialization vs Latency**: Baseline provides quick completions.",
            "  However, when tasks require deep multi-step retrieval, single-agent suffers from",
            "  context dilution. Multi-agent divides the work into specialized roles (Researcher,",
            "  Analyst, Writer), giving higher analytical depth and grounded citations.",
            "- **Cost & Efficiency**: Multi-agent incurs higher token cost due to handoffs.",
            "  This is justified for research where citation fidelity is paramount.",
            "",
            "## 3. Failure Modes & Production Guardrails",
            "",
            "1. **Infinite Routing Loop**: Occurs when Supervisor fails to stop properly.",
            "   *Guardrail*: Hard limit `max_iterations = 6` that forces termination.",
            "2. **Context Bloat / Handoff Loss**: Unformatted prompt dumps passed between agents.",
            "   *Guardrail*: Typed Pydantic `ResearchState` with explicit fields.",
            "3. **Cascading Hallucinations**: Early errors propagate downstream.",
            "   *Guardrail*: Grounding with `SourceDocument` IDs and Critic agent validation.",
            "",
            "## 4. Exit Ticket",
            "",
            "- **Khi nào NÊN dùng Multi-Agent?**: Bài toán phức tạp cần nhiều bước riêng biệt",
            "  (thu thập -> phản biện -> viết báo cáo trích dẫn) hoặc cần modularity cao.",
            "- **Khi nào KHÔNG NÊN dùng Multi-Agent?**: Tác vụ đơn giản, câu hỏi ngắn, yêu cầu",
            "  độ trễ cực thấp hoặc giới hạn ngân sách chi phí token nghiêm ngặt.",
        ]
    )
    return "\n".join(lines) + "\n"
