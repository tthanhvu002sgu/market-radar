# Domain framing: Chất lượng ứng viên swing

## Gap report
- D-1 High: `screening_rules.py` coi gần MA ±2,5% là pullback; trạng thái confirmed chỉ cần phiên tăng và trên MA. Chưa chứng minh chạm và bật lại. Sửa: xác nhận phản ứng OHLC theo chiều setup trước khi ưu tiên.
- D-2 High: score cộng RS thị trường, RS ngành và bonus; extension, invalidation và khoảng trống đến cản không tham gia lựa chọn. SWKS snapshot 6 đứng đầu, cách MA20 4,36 ATR, checklist nến fail. Sửa: gate chất lượng trước xếp hạng.
- D-3 High: 197 dòng setup, 156 setup chưa xác nhận, 37 confirmed, 4 watchlist tại 2026-09-11. Chưa có shortlist và giới hạn trùng ngành. Sửa: ba mức chất lượng, shortlist tối đa 10 mã, tối đa 2 mã/nhóm ngành nhỏ.
- D-4 High: chỉ 2 ngày snapshot độc lập; outcomes dài hạn chưa hoàn thành. Chưa đủ bằng chứng cải thiện lợi nhuận. Sửa: không tối ưu ngưỡng trên mẫu này; kiểm thử hành vi và theo dõi forward riêng.

## 1. Executive frame
- User outcome: giảm thời gian rà soát cả bốn vấn đề: xác nhận, mua đuổi, rủi ro/lợi nhuận, trùng cơ hội.
- Audience: người dùng radar S&P 500 EOD, quyết định xem chart nào trước.
- Fidelity: Operational, hỗ trợ rà soát; không tự đặt lệnh hay dự báo xác suất thắng.
- Primary domain: phân loại setup; secondary: UX ưu tiên, chất lượng dữ liệu tài chính.
- Verdict: READY WITH ASSUMPTIONS cho lớp sàng lọc rà soát; chưa đủ bằng chứng promotion chiến lược giao dịch.

## 2. What an expert sees
- Giá gần MA chưa chứng minh pullback; nhãn triggered chưa chứng minh điểm vào hiện tại hợp lý.
- RS cao không được bù cho mức vô hiệu sai chiều hoặc giá đã chạy xa.
- R/R cần mốc cản có thật phía trước; không tự tạo target 2R để đạt gate 2R.
- Nến breakout vượt đỉnh cũ thường chưa có kháng cự phía trên trong dữ liệu này: ghi thiếu target, chuyển chờ kiểm tra.
- Không coi thiếu lịch earnings là không có earnings; shortlist giới hạn ngành chỉ giảm lặp, không đo tương quan danh mục.

## 3. Minimum domain model
### Boundary and entities
Một candidate/setup tại một phiên đóng cửa, evidence và FA đã lưu. Không lấy giá hoặc FA hiện tại để sửa lịch sử. Không thay scanner gốc, base detector, execution hay outcomes gốc.
### State / process
Raw candidate → không ưu tiên (vi phạm gate) / chờ xác nhận (thiếu bằng chứng) / đạt bộ lọc → xếp ưu tiên → shortlist. Có thể 0 mã đạt. Danh sách đầy đủ vẫn truy cập được.
### Governing logic
Entry tham chiếu = max(close, trigger) cho long, min(close, trigger) cho short. Risk = side × (entry − invalidation), side = +1 long / −1 short. Room = side × (cản − entry). Room/risk chỉ tính khi cả hai dương. Đây là khoảng trống kỹ thuật, chưa tính phí/slippage và không phải kỳ vọng lợi nhuận.
### Inputs
| Input | Meaning | Type / unit | Range / default | Source | Confidence |
|---|---|---|---|---|---|
| Close, trigger, invalidation, ATR | Mốc phân tích | USD | hữu hạn, dương; thiếu → chờ | snapshot | quan sát / heuristic |
| OHLC, vị trí đóng cửa | Phản ứng tại trigger | USD / % | hợp lệ; không fallback xác nhận | evidence snapshot | quan sát |
| Volume, extension | Thanh khoản và chạy xa | USD/ngày, x ATR | $10M; 1 ATR trigger; 2 ATR MA20 | snapshot | ngưỡng đề xuất |
| Cản phía trước | Khoảng trống kỹ thuật | USD | room/risk ≥1,5 | support/resistance snapshot | proxy, chưa phải target kiểm chứng |
| Risk | Khoảng tới vô hiệu | ATR / % entry | ≤2,5 ATR và ≤6% | tính từ mốc | ngưỡng đề xuất |
| Earnings | Ngày đến sự kiện | ngày lịch | >7; thiếu/âm → chờ | FA snapshot | nguồn ước tính |
### Outputs
| Output | Meaning / interpretation | Type / unit | Validation |
|---|---|---|---|
| quality tier, reasons | Đạt/chờ/không ưu tiên và nguyên nhân | enum/list | fixtures mỗi gate |
| risk, room/risk, entry | Giá trị tham chiếu để so sánh | % / ATR / ratio / USD | kiểm tra long-short đối xứng |
| shortlist | ≤10 mã, ≤2 mỗi ngành nhỏ | danh sách | không trùng symbol, không ép đủ |
### Constraints, edge cases, and misuse
NaN/inf/thiếu dữ liệu không được pass; invalidation sai chiều loại; không có cản không suy thành room vô hạn. Snapshot cũ đánh giá lại bằng quality version hiện tại, không tuyên bố là backtest point-in-time. Giá fill có thể khác entry tham chiếu. Không dùng chỉ đếm số lượng giảm để tuyên bố edge.

## 4. Evidence and uncertainty ledger
| Claim / decision | Class | Evidence | Impact if wrong | Validation / owner |
|---|---|---|---|---|
| Cả bốn vấn đề đều gây mất thời gian | user fact | trả lời người dùng | sai mục tiêu | người dùng đánh giá shortlist |
| 197 setup, 156 chưa xác nhận | verified fact | SQLite snapshot 6, chỉ đọc | audit sai | truy vấn tái lập |
| ATR đo biến động, không dự báo hướng | verified fact | [Fidelity ATR](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/atr) | diễn giải sai | dùng để chuẩn hóa khoảng cách |
| Stop không đảm bảo giá khớp | verified fact | [FINRA stop orders](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets) | risk bị hiểu thành giới hạn chắc chắn | nhãn tham chiếu, không simulation P&L |
| Ngưỡng số và số lượng shortlist | proposal | cấu hình ban đầu chưa tối ưu | bỏ lỡ setup tốt | theo dõi ngoài mẫu, người dùng điều chỉnh sau |
| Room/risk tới cản là proxy hữu ích | assumption | có cản snapshot, không có target model | loại breakout thiếu target | cho phép xem nhóm chờ |

## 5. Feature map
### Core
Gate phản ứng OHLC, extension, risk/room; xếp theo gate trước RS; giới hạn số mã/nhóm để giảm lặp.
### Trust
Lý do đầy đủ, version, xuất CSV, mở tất cả, giữ nguyên dữ liệu scanner và outcomes.
### Explore
Chuyển giữa ưu tiên, đạt bộ lọc, chờ, không ưu tiên, toàn bộ; bật/tắt giới hạn lặp ngành.
### Later / out of scope
Tối ưu lợi nhuận, target theo cấu trúc nhiều khung, tương quan thực, execution, dữ liệu thị trường mới, sửa base detector.

## 6. Acceptance and validation
Fixtures long/short; giả confirmed nhưng không có phản ứng; thiếu/NaN; invalidation sai chiều; target phía sau; score cực cao vẫn bị gate; dedup, cap và deterministic ties. Regression suite. Báo số lượng trước/sau trên snapshot giữ nguyên. Đánh giá forward trên nhiều phiên và chế độ thị trường trước tuyên bố edge; người có chuyên môn giao dịch cần rà soát trước dùng làm quy tắc đặt lệnh.

## 7. Open decisions
Đã xác nhận cả bốn nguyên nhân. Dùng các ngưỡng đề xuất trên làm mặc định có thể đảo lại; không chờ người dùng tự thiết kế công thức.

## 8. Readiness score
| Dimension | Score | Gap |
|---|---|---|
| Outcome/audience/fidelity | 2 | — |
| Boundary/state | 2 | — |
| Logic | 2 | định nghĩa tường minh, chưa chứng minh edge |
| Inputs/outputs | 2 | — |
| Failures | 2 | — |
| Evidence | 1 | chưa kiểm định ngưỡng |
| Validation | 1 | kiểm thử hành vi trước, forward sau |
| Scope | 2 | — |
Total 14/16: READY WITH ASSUMPTIONS cho lọc rà soát có thể đảo lại.

## 9. Build handoff
Module thuần tính chất lượng từ candidate, cấu hình version riêng; tích hợp UI và evidence các lần scan sau; shortlist mặc định, lý do và risk/room ngay bảng/thẻ, CSV có metadata. Không ghi lại DB cũ. Acceptance theo mục 6; báo rõ thiếu lịch sử để kết luận lợi nhuận.

## Implementation and verification
- Đã thêm `analytics/candidate_quality.py`, gắn quality version vào evidence khi scan, áp dụng phân loại và shortlist trong trang Ứng viên; giữ score/rank scanner gốc và thêm review rank riêng. Không cập nhật nội dung snapshot lịch sử.
- Snapshot #6, as_of 2026-09-11: 197 setup → 0 đạt, 36 chờ, 161 không ưu tiên. Không nới ngưỡng theo kết quả này để ép có mã.
- Lý do có thể chồng lặp: 180 thiếu xác nhận theo tiêu chí mới; 117 room/risk thấp; 102 risk rộng; 58 thiếu cản phía trước; 33 xa MA20; 18 xa trigger; 4 mâu thuẫn; 1 thiếu lịch earnings.
- Ví dụ SWKS: score cao không vượt gate extension MA20; không tự suy ra target từ đỉnh vừa phá.
- `python -m pytest tests/ -q`: 223 passed, 2 cảnh báo deprecation từ protobuf. Bao gồm kiểm tra tương tác Streamlit: shortlist mặc định chỉ có mã đạt, chuyển Không ưu tiên hiển thị mã bị loại và lý do.
- Giới hạn: dữ liệu chỉ có hai phiên snapshot độc lập; 0 mã đạt có thể phản ánh điều kiện phiên và sự chặt của mô hình/ngưỡng. Cần review forward nhiều phiên để kiểm tra tỷ lệ bỏ sót. Bộ phận Outcomes hiện vẫn đo scanner gốc, không được dùng để khẳng định hiệu quả `review-v1`.
