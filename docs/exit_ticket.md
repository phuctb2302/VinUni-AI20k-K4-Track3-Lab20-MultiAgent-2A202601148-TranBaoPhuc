# Exit Ticket

Học viên: Trần Bảo Phúc

Trả lời dựa trên số liệu benchmark thực tế đã chạy trong `reports/benchmark_report.md` và
`reports/trace_20260820_175739.json` (cùng một query, so sánh baseline vs multi-agent).

## 1. Case nào nên dùng multi-agent? Vì sao?

Nên dùng khi **task cần citation / bằng chứng có thể truy vết**, và khi các bước xử lý đòi hỏi
tiêu chí đánh giá khác nhau đến mức khó gộp vào một prompt duy nhất mà không mất chất lượng.

**Bằng chứng cụ thể từ benchmark:** Cùng một câu hỏi *"Research GraphRAG state-of-the-art"*,
baseline single-agent cho **citation coverage = 0%** (model trả lời hoàn toàn từ kiến thức nội
tại, không có bước tra cứu nguồn nào tách biệt để trích dẫn), trong khi multi-agent đạt
**Quality 10.0/10** với 5 nguồn tài liệu được trích dẫn inline vì có Researcher tách riêng gắn
`[Source 1]`, `[Source 2]`... vào state trước khi Analyst và Writer sử dụng.

Cụ thể hơn, multi-agent hợp lý khi:

- **Output cần audit được**: Research report, tài liệu pháp lý, tài liệu y tế — citation coverage
  đo được là yêu cầu cứng, không phải "nice to have".
- **Có bước cần "góc nhìn thứ hai" độc lập**: Analyst trong hệ thống có nhiệm vụ tìm bằng chứng
  yếu / mâu thuẫn trong chính research notes — Researcher khó tự phát hiện vì thiên lệch xác
  nhận (confirmation bias) nếu gộp chung một agent.
- **Chi phí tăng thêm chấp nhận được**: Trong bài đo thực tế, cost tăng ~9.2x (từ $0.00005 lên
  $0.00046), latency tăng ~2.7x (từ 3.99s lên 5.19s từ 3 lệnh gọi LLM tuần tự thay vì 1) —
  chấp nhận được khi giá trị trả về là trace/citation kiểm chứng được.
- **Task phức tạp đòi hỏi nhiều bước chuyên biệt**: Thu thập tài liệu → phân tích / phản biện →
  tổng hợp báo cáo trích dẫn. Mỗi bước có tiêu chí đánh giá riêng biệt và khó gộp vào 1 prompt.

## 2. Case nào không nên dùng multi-agent? Vì sao?

Không nên dùng khi task đơn giản, không cần trích dẫn, và latency / cost quan trọng hơn khả
năng audit.

**Bằng chứng từ benchmark của tôi**: Baseline cho quality proxy 5.0/10 chỉ trong 3.99s với
cost $0.00005 — tức là "đủ dùng" cho câu hỏi giải thích khái niệm thông thường. Trả thêm
~9.2x cost và ~2.7x latency để lấy quality 10.0 chỉ hợp lý nếu citation thực sự có giá trị
với người dùng cuối.

Cụ thể hơn, nên tránh multi-agent khi:

- **Task không có "câu trả lời sai lệch tốn kém"**: Hỏi định nghĩa, tóm tắt nhanh, brainstorm
  ý tưởng — một LLM call là đủ, chia nhỏ chỉ tạo thêm overhead điều phối (guardrail, retry,
  trace) mà không đổi lại chất lượng tương xứng.
- **Latency là yêu cầu cứng**: Pipeline tuần tự Researcher → Analyst → Writer cộng dồn latency
  của cả 3 LLM call, tăng ~2.7x so với baseline. Trong ngữ cảnh latency-sensitive (trả lời
  realtime), muốn giữ multi-agent sẽ cần chạy song song các bước độc lập, tính năng mà hệ
  thống hiện tại chưa implement.
- **Nguồn dữ liệu để Researcher tra cứu không đáng tin**: Lúc đó multi-agent không tạo thêm giá
  trị citation nào so với baseline mà còn tốn thêm tiền/thời gian, đồng thời tăng rủi ro
  cascade hallucination nếu agent "tưởng" mình có nguồn tốt trong khi nguồn thực ra nghèo/nhiễu.
- **Ngân sách token bị giới hạn nghiêm ngặt**: Cost tăng ~9.2x ở thực nghiệm này — với scale
  lớn (hàng nghìn query/ngày), con số này là không thể bỏ qua.
