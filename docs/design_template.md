# Design Template

Học viên: Trần Bảo Phúc

## Problem

Xây dựng hệ thống **Research Assistant** có khả năng nhận một câu hỏi nghiên cứu phức tạp,
tự động thu thập tài liệu từ offline corpus / web search, phân tích và tổng hợp thành báo cáo
cuối cùng có trích dẫn nguồn. So sánh hiệu quả giữa single-agent baseline và multi-agent workflow
theo các metric định lượng: latency, cost, quality, citation coverage, failure rate.

## Why multi-agent?

Single-agent gặp vấn đề **context dilution** khi gộp chung 3 nhiệm vụ khác nhau vào 1 prompt:
thu thập tài liệu (cần breadth), phân tích phản biện (cần critical thinking), và viết báo cáo
(cần coherence). Kết quả thực đo: baseline single-agent cho **citation coverage = 0%** vì không
có bước tách biệt nào để gán source ID vào state trước khi viết. Multi-agent chia luồng thành
3 agent chuyên biệt với input/output rõ ràng → **citation coverage = 100%** với cùng một query.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| **Supervisor** | Điều phối routing, kiểm tra guardrail | `ResearchState` (toàn bộ) | Cập nhật `route_history`, `trace` | Infinite loop nếu không có `max_iterations` |
| **Researcher** | Thu thập tài liệu qua SearchClient, tổng hợp research notes bằng LLM | `state.request.query`, `state.request.max_sources` | `state.sources`, `state.research_notes` | SearchClient fail (network, key lỗi) → `state.errors` |
| **Analyst** | Phân tích trade-off, tìm mâu thuẫn và điểm yếu trong research notes | `state.research_notes`, `state.request.query` | `state.analysis_notes` | LLM call fail → ghi lỗi, Supervisor retry |
| **Writer** | Tổng hợp báo cáo cuối có inline citations `[Source N]` và phần References | `state.research_notes`, `state.analysis_notes`, `state.sources` | `state.final_answer` | Thiếu `research_notes` / `analysis_notes` → báo cáo thiếu chiều sâu |

## Shared state

`ResearchState` (Pydantic model) — single source of truth truyền qua tất cả các node:

| Field | Type | Lý do cần |
|---|---|---|
| `request` | `ResearchQuery` | Giữ query, audience, max_sources gốc — không bị biến đổi qua các bước |
| `iteration` | `int` | Đếm số lần Supervisor route — guardrail `max_iterations` dựa vào đây |
| `route_history` | `list[str]` | Audit trail: xem Supervisor đã routing qua đâu để debug |
| `sources` | `list[SourceDocument]` | Danh sách tài liệu Researcher tìm được — Writer dùng để tạo References |
| `research_notes` | `str \| None` | Output của Researcher — Analyst và Writer đọc vào |
| `analysis_notes` | `str \| None` | Output của Analyst — Writer đọc vào để viết báo cáo có phân tích sâu |
| `final_answer` | `str \| None` | Output của Writer — điều kiện để Supervisor route `done` |
| `agent_results` | `list[AgentResult]` | Token usage + cost của từng agent — dùng cho benchmark |
| `trace` | `list[dict]` | Tất cả trace events (`supervisor_route`, `researcher_completed`...) |
| `errors` | `list[str]` | Danh sách lỗi gặp phải — không raise crash, ghi nhận để debug |

## Routing policy

```text
START
  │
  ▼
[Supervisor]
  │
  ├─ iteration >= max_iterations? ──────────────────────────► DONE (guardrail)
  │
  ├─ sources == [] or research_notes is None? ──────────────► [Researcher] ─┐
  │                                                                          │
  ├─ analysis_notes is None? ◄──────────────────────────────────────────────┘
  │  ────────────────────────────────────────────────────────► [Analyst] ───┐
  │                                                                          │
  ├─ final_answer is None? ◄─────────────────────────────────────────────────┘
  │  ────────────────────────────────────────────────────────► [Writer] ────┐
  │                                                                          │
  └─ all done? ◄──────────────────────────────────────────────────────────-─┘
     ────────────────────────────────────────────────────────► DONE ✓
```

## Guardrails

- **Max iterations:** `max_iterations = 6` (default) — Supervisor force route `done` khi đạt giới
  hạn, ghi lỗi vào `state.errors`. Cấu hình qua biến môi trường `MAX_ITERATIONS`.
- **Timeout:** `timeout_seconds = 60` (default) — giới hạn tổng thời gian chạy workflow.
  Cấu hình qua biến môi trường `TIMEOUT_SECONDS`.
- **Retry:** `LLMClient` dùng `tenacity` với exponential backoff, retry tối đa 3 lần khi gặp
  lỗi tạm thời (rate limit, network timeout).
- **Fallback:** Node wrapper bắt `AgentExecutionError`, không để exception crash graph — ghi
  lỗi vào `state.errors` và trả state về Supervisor nguyên vẹn.
- **Validation:** `ResearchState` dùng Pydantic — tất cả input/output có type hints, không thể
  truyền dữ liệu sai kiểu giữa các agent.

## Benchmark plan

| Query | Metric | Baseline Expected | Multi-Agent Expected |
|---|---|---|---|
| "Research GraphRAG state-of-the-art" | Latency (s) | < 10s | < 15s |
| "Research GraphRAG state-of-the-art" | Cost (USD) | < $0.001 | < $0.005 |
| "Research GraphRAG state-of-the-art" | Quality (0-10) | 4-6 (no citations) | 8-10 (with citations) |
| "Research GraphRAG state-of-the-art" | Citation coverage | 0% | > 80% |
| "Research GraphRAG state-of-the-art" | Failure rate | 0% | 0% |

**Kết quả thực tế** (từ `reports/benchmark_report.md`):

| Run | Latency | Cost (USD) | Quality | Citations | Fail Rate |
|---|---:|---:|---:|---:|---:|
| Single-Agent Baseline | 3.99s | $0.00005 | 5.0/10 | 0% | 0% |
| Multi-Agent System | 5.19s | $0.00046 | 10.0/10 | 100% | 0% |

