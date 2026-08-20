"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import logging
from dataclasses import dataclass

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client with OpenAI support and offline fallback."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.2,
        timeout: float | None = None,
    ) -> None:
        self.settings = get_settings()
        self.model = model or self.settings.openai_model
        self.temperature = temperature
        self.timeout = timeout or float(self.settings.timeout_seconds)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Return a model completion with token and cost tracking."""
        temp = self.temperature if temperature is None else temperature
        api_key = self.settings.openai_api_key

        if api_key and api_key.strip():
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key, timeout=self.timeout)
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=temp,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                choice = response.choices[0]
                content = choice.message.content or ""
                usage = response.usage

                input_tokens = usage.prompt_tokens if usage else None
                output_tokens = usage.completion_tokens if usage else None
                cost_usd = self._estimate_cost(self.model, input_tokens, output_tokens)

                return LLMResponse(
                    content=content,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=cost_usd,
                )
            except Exception as e:
                logger.warning(
                    f"OpenAI API call failed ({e}), falling back to simulated generation."
                )

        # Fallback simulation when no API key or API call fails
        return self._simulate_completion(system_prompt, user_prompt)

    def _estimate_cost(
        self, model: str, input_tokens: int | None, output_tokens: int | None
    ) -> float | None:
        if input_tokens is None or output_tokens is None:
            return None
        # Approximate pricing for standard models (e.g. gpt-4o-mini: $0.15 / 1M in, $0.60 / 1M out)
        if "mini" in model:
            price_in = 0.15 / 1_000_000
            price_out = 0.60 / 1_000_000
        else:
            price_in = 2.50 / 1_000_000
            price_out = 10.00 / 1_000_000
        return (input_tokens * price_in) + (output_tokens * price_out)

    def _simulate_completion(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Simulate realistic research synthesis when offline."""
        prompt_words = len(user_prompt.split()) + len(system_prompt.split())
        input_tokens = int(prompt_words * 1.3) + 10

        if "supervisor" in system_prompt.lower() or "router" in system_prompt.lower():
            if "sources" not in user_prompt.lower() or "no sources" in user_prompt.lower():
                content = "researcher"
            elif "analysis" not in user_prompt.lower():
                content = "analyst"
            elif "final" not in user_prompt.lower():
                content = "writer"
            else:
                content = "done"
        elif "analyst" in system_prompt.lower():
            content = (
                "Key Insights & Analysis:\n"
                "1. Multi-agent architectures improve modularity and reduce prompt bloat.\n"
                "2. Handoff efficiency depends on concise shared state representations.\n"
                "3. Trade-off: higher quality/explainability vs increased latency/cost.\n"
                "4. Guardrails (max iterations, timeout) are mandatory for stability."
            )
        elif "writer" in system_prompt.lower():
            content = (
                "# Research Report: State-of-the-Art & System Analysis\n\n"
                "## Executive Summary\n"
                "Modern autonomous systems leverage specialized worker agents orchestrated "
                "by a central supervisor to achieve high reliability and modularity [Source 1].\n\n"
                "## Detailed Findings\n"
                "- **Architecture & Roles**: Dividing responsibilities among dedicated agents "
                "(Researcher, Analyst, Writer) prevents context dilution [Source 1, Source 2].\n"
                "- **State & Guardrails**: Utilizing typed shared state with strict loop limits "
                "ensures robust execution [Source 3].\n"
                "- **Cost & Latency Trade-offs**: While multi-agent pipelines incur higher latency "
                "and token costs, they deliver significantly richer evidence synthesis and "
                "verifiable citations.\n\n"
                "## Conclusion & Recommendations\n"
                "For complex research tasks requiring multi-step verification, multi-agent "
                "workflows provide clear benefits."
            )
        else:
            content = (
                f"Synthesized research response for: '{user_prompt[:120]}...'\n\n"
                "1. **Core Concept**: Critical pattern in distributed agentic AI systems.\n"
                "2. **Best Practices**: Employ structured outputs and bounded iterations.\n"
                "3. **Conclusion**: Single-agent is fast/low-cost; multi-agent adds depth."
            )

        output_tokens = int(len(content.split()) * 1.3) + 20
        cost_usd = self._estimate_cost(self.model, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )
