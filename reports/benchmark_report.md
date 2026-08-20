# Benchmark Report: Single-Agent Baseline vs Multi-Agent Research System

## 1. Quantitative Comparison

| Run | Latency | Cost (USD) | Quality | Citations | Fail Rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| **Single-Agent Baseline** | 3.99s | $0.00005 | 5.0/10 | 0% | 0% | Routes: 0 steps, 0 sources |
| **Multi-Agent System** | 5.19s | $0.00046 | 10.0/10 | 100% | 0% | Routes: 4 steps, 5 sources |

## 2. Key Findings & Trade-off Analysis

- **Specialization vs Latency**: Baseline provides quick completions.
  However, when tasks require deep multi-step retrieval, single-agent suffers from
  context dilution. Multi-agent divides the work into specialized roles (Researcher,
  Analyst, Writer), giving higher analytical depth and grounded citations.
- **Cost & Efficiency**: Multi-agent incurs higher token cost due to handoffs.
  This is justified for research where citation fidelity is paramount.

## 3. Failure Modes & Production Guardrails

1. **Infinite Routing Loop**: Occurs when Supervisor fails to stop properly.
   *Guardrail*: Hard limit `max_iterations = 6` that forces termination.
2. **Context Bloat / Handoff Loss**: Unformatted prompt dumps passed between agents.
   *Guardrail*: Typed Pydantic `ResearchState` with explicit fields.
3. **Cascading Hallucinations**: Early errors propagate downstream.
   *Guardrail*: Grounding with `SourceDocument` IDs and Critic agent validation.

## 4. Exit Ticket

- **Khi nào NÊN dùng Multi-Agent?**: Bài toán phức tạp cần nhiều bước riêng biệt
  (thu thập -> phản biện -> viết báo cáo trích dẫn) hoặc cần modularity cao.
- **Khi nào KHÔNG NÊN dùng Multi-Agent?**: Tác vụ đơn giản, câu hỏi ngắn, yêu cầu
  độ trễ cực thấp hoặc giới hạn ngân sách chi phí token nghiêm ngặt.
