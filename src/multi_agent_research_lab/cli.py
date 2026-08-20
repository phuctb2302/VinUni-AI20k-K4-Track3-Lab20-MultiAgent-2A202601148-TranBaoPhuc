"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline with real LLM completion and metric reporting."""
    import time

    from multi_agent_research_lab.services.llm_client import LLMClient

    _init()
    request = _parse_query(query)
    state = ResearchState(request=request)

    llm = LLMClient()
    start_time = time.perf_counter()

    system_prompt = (
        "You are an expert research assistant. Analyze the user query directly "
        "and provide a clear, structured, and comprehensive answer."
    )
    response = llm.complete(system_prompt=system_prompt, user_prompt=request.query)
    latency = time.perf_counter() - start_time

    state.final_answer = response.content
    cost_str = f"${response.cost_usd:.5f}" if response.cost_usd is not None else "N/A"
    tokens_str = (
        f"Prompt: {response.input_tokens or 'N/A'}, Completion: {response.output_tokens or 'N/A'}"
    )

    console.print(
        Panel.fit(state.final_answer, title="Single-Agent Baseline Result", border_style="cyan")
    )
    console.print(
        Panel.fit(
            f"⏱️  Latency: {latency:.2f}s | 💰 Cost: {cost_str} | 🏷️  Tokens: {tokens_str}",
            title="Baseline Metrics",
            border_style="green",
        )
    )


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    save_trace: Annotated[
        bool, typer.Option("--save-trace", help="Auto-save trace to reports/")
    ] = True,
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    import time

    request = _parse_query(query)
    state = ResearchState(request=request)

    start_time = time.perf_counter()
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)

    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc

    latency = time.perf_counter() - start_time
    total_in = sum(r.metadata.get("input_tokens", 0) or 0 for r in result.agent_results)
    total_out = sum(r.metadata.get("output_tokens", 0) or 0 for r in result.agent_results)
    total_cost = sum(r.metadata.get("cost_usd", 0.0) or 0.0 for r in result.agent_results)

    console.print(
        Panel.fit(
            result.final_answer or "No final answer generated.",
            title="Multi-Agent Final Answer",
            border_style="cyan",
        )
    )
    console.print(
        Panel.fit(
            f"🔄  Route History: {' ➔ '.join(result.route_history)}\n"
            f"📚  Sources Gathered: {len(result.sources)}\n"
            f"⏱️  Latency: {latency:.2f}s | 💰 Cost: ${total_cost:.5f}\n"
            f"🏷️  Tokens: {total_in + total_out} (Prompt: {total_in}, Completion: {total_out})",
            title="Multi-Agent Execution Metrics",
            border_style="green",
        )
    )

    # Auto-export trace to reports/ for submission evidence
    if save_trace:
        from multi_agent_research_lab.observability.tracing import export_trace_report

        trace_path = export_trace_report(result, latency)
        console.print(f"[bold green]✓ Trace exported → {trace_path}[/bold green]")


@app.command("benchmark")
def benchmark(
    query: Annotated[
        str,
        typer.Option("--query", "-q", help="Research query for benchmark"),
    ] = "Research GraphRAG state-of-the-art and multi-agent system guardrails",
    output_path: Annotated[
        str,
        typer.Option("--output", "-o", help="Output path for benchmark report"),
    ] = "reports/benchmark_report.md",
) -> None:
    """Run comparative benchmark between Single-Agent Baseline and Multi-Agent System."""
    from pathlib import Path

    from multi_agent_research_lab.evaluation.benchmark import run_benchmark
    from multi_agent_research_lab.evaluation.report import render_markdown_report
    from multi_agent_research_lab.services.llm_client import LLMClient

    _init()
    console.print(f"[bold green]Starting benchmark run on query:[/bold green] {query}")

    # 1. Runner for Baseline
    def run_single(q: str) -> ResearchState:
        llm = LLMClient()
        state = ResearchState(request=ResearchQuery(query=q))
        resp = llm.complete(
            system_prompt=(
                "You are a single-agent research assistant. Answer concisely and clearly."
            ),
            user_prompt=q,
        )
        state.final_answer = resp.content
        state.agent_results.append(
            type(
                "Result",
                (),
                {
                    "metadata": {
                        "input_tokens": resp.input_tokens,
                        "output_tokens": resp.output_tokens,
                        "cost_usd": resp.cost_usd,
                    }
                },
            )()  # type: ignore
        )
        return state

    # 2. Runner for Multi-Agent
    def run_multi(q: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=q))
        wf = MultiAgentWorkflow()
        return wf.run(state)

    console.print("Running Single-Agent Baseline...")
    _, baseline_metrics = run_benchmark("Single-Agent Baseline", query, run_single)

    console.print("Running Multi-Agent System...")
    _, multi_metrics = run_benchmark("Multi-Agent System", query, run_multi)

    metrics_list = [baseline_metrics, multi_metrics]
    report_content = render_markdown_report(metrics_list)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(report_content, encoding="utf-8")

    console.print(
        Panel.fit(report_content, title="Generated Benchmark Report", border_style="cyan")
    )
    console.print(
        f"[bold green]✓ Benchmark report successfully written to {output_path}[/bold green]"
    )


if __name__ == "__main__":
    app()
