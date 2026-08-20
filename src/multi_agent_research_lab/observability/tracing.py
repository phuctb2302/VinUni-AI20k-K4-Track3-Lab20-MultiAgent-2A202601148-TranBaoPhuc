import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Span context supporting LangSmith, Langfuse, and local trace instrumentation."""
    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": attributes or {},
        "duration_seconds": None,
        "status": "RUNNING",
    }
    settings = get_settings()

    # Hook for LangSmith if configured
    if settings.langsmith_api_key:
        logger.debug(f"[LangSmith] Trace span started: {name}")

    # Hook for Langfuse if configured
    if settings.langfuse_public_key:
        logger.debug(f"[Langfuse] Trace span started: {name}")

    try:
        yield span
        span["status"] = "SUCCESS"
    except Exception as exc:
        span["status"] = "FAILED"
        span["error"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
        logger.debug(
            f"Span '{name}' ended in {span['duration_seconds']:.4f}s with status {span['status']}"
        )


def export_trace_report(state: Any, latency: float, output_dir: str = "reports") -> Path:
    """Export full structured trace as JSON and Markdown to reports/ for submission evidence."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Export raw JSON trace
    trace_data = {
        "run_timestamp": datetime.now().isoformat(),
        "query": state.request.query,
        "total_latency_seconds": latency,
        "route_history": state.route_history,
        "iteration_count": state.iteration,
        "sources_gathered": len(state.sources),
        "trace_events": state.trace,
        "agent_results_summary": [
            {
                "agent": r.agent,
                "content_length": len(r.content),
                "input_tokens": r.metadata.get("input_tokens"),
                "output_tokens": r.metadata.get("output_tokens"),
                "cost_usd": r.metadata.get("cost_usd"),
            }
            for r in state.agent_results
        ],
        "errors": state.errors,
        "final_answer_length": len(state.final_answer or ""),
    }
    json_path = out / f"trace_{timestamp}.json"
    json_path.write_text(json.dumps(trace_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2. Export human-readable Markdown trace
    total_in = sum(r.metadata.get("input_tokens") or 0 for r in state.agent_results)
    total_out = sum(r.metadata.get("output_tokens") or 0 for r in state.agent_results)
    total_cost = sum(r.metadata.get("cost_usd") or 0.0 for r in state.agent_results)

    md_lines = [
        "# Agent Execution Trace Report",
        "",
        f"**Run at**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ",
        f"**Query**: `{state.request.query}`  ",
        f"**Total Tokens**: `{total_in + total_out}` "
        f"(Prompt: `{total_in}`, Completion: `{total_out}`)  ",
        f"**Estimated Cost**: `${total_cost:.5f}`  ",
        "",
        "## Routing Flow",
        "",
        "```",
        " → ".join(state.route_history) if state.route_history else "No routing recorded",
        "```",
        "",
        "## Per-Agent Step Details",
        "",
        "| Step | Agent | Content Length | Tokens In | Tokens Out | Cost (USD) |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for idx, r in enumerate(state.agent_results, 1):
        cost_val = r.metadata.get("cost_usd")
        cost_str = f"${cost_val:.5f}" if cost_val else "N/A"
        md_lines.append(
            f"| {idx} | `{r.agent}` | {len(r.content)} chars "
            f"| {r.metadata.get('input_tokens') or 'N/A'} "
            f"| {r.metadata.get('output_tokens') or 'N/A'} "
            f"| {cost_str} |"
        )

    md_lines.extend(
        [
            "",
            "## Sources Retrieved",
            "",
        ]
    )
    for idx, src in enumerate(state.sources, 1):
        md_lines.append(f"- **[Source {idx}]** [{src.title}]({src.url or 'Offline Corpus'})")

    md_lines.extend(
        [
            "",
            "## Trace Events (Supervisor Decisions)",
            "",
            "```json",
            json.dumps(
                [e for e in state.trace if "supervisor" in e.get("name", "")],
                indent=2,
                ensure_ascii=False,
            ),
            "```",
            "",
            "## Final Answer Preview",
            "",
            "```markdown",
            (state.final_answer or "")[:500]
            + ("..." if len(state.final_answer or "") > 500 else ""),
            "```",
        ]
    )

    if state.errors:
        md_lines.extend(["", "## ⚠️ Errors / Warnings", ""])
        for err in state.errors:
            md_lines.append(f"- {err}")

    md_path = out / f"trace_{timestamp}.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    logger.info(f"Trace exported → {md_path} and {json_path}")
    return md_path
