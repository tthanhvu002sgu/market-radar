# Kiểm tra lại triển khai gap D-1 đến D-5

## Phần 1: Bảng tổng hợp rủi ro logic

Phạm vi: thay đổi chưa commit trên HEAD `665d9ff`, tập trung đường đi từ scanner → snapshot → shortlist → chi tiết setup → kế hoạch/nhật ký → outcomes. Chọn các luồng này vì lỗi có thể làm hỏng thao tác chính hoặc sai dữ liệu quyết định. Không audit toàn repository; bỏ qua lỗi nhỏ và phong cách theo yêu cầu người dùng. Không sửa mã sản phẩm.

**Kết luận: chưa nên đóng toàn bộ gap.** D-1 đã được nối pipeline và UI; D-2 đã có lưu luận điểm và mô hình theme; D-3 có calculator/phiếu kế hoạch nhưng còn sai liên kết; D-4 mới hoàn thành một phần; D-5 đã thêm thống kê theo playbook, chưa đồng nghĩa ngưỡng được kiểm định.

| ID | Vị trí | Loại lỗi | Mức độ | Tác động | Bằng chứng |
|---|---|---|---|---|---|
| LOGIC-001 | `app/components/setup_detail.py:747` | Truy cập None | Cao | Không mở/lưu được nhật ký đầu tiên của mã | Đã xác nhận bằng tái hiện AppTest |
| LOGIC-002 | `app/components/candidate_cards.py:659` | Nhầm định danh snapshot/setup | Cao | Hiện sai tập shortlist đã đóng băng, có thể quá 10 mã và lẫn setup | Đã xác nhận bằng phân tích tĩnh |
| LOGIC-003 | `app/components/setup_detail.py:675` | Risk không theo kế hoạch nhập | Cao | Tiền rủi ro trên màn hình khác kế hoạch được lưu | Đã xác nhận bằng phân tích tĩnh; kiểm tra số học độc lập |
| LOGIC-004 | `analytics/signal_outcomes.py:697` | Ghép quyết định sai phiên | Trung bình, module chưa tích hợp | Quyết định ở phiên sau thay cho phiên trước | Đã xác nhận bằng tái hiện |
| LOGIC-005 | `analytics/signal_outcomes.py:774` | Sai mốc thời gian kết quả fill | Trung bình, module chưa tích hợp | Tính lợi suất thực bằng giá đóng trước ngày khớp | Đã xác nhận bằng tái hiện |

### Kiểm chứng và độ bao phủ

- `python -m pytest tests/test_gap_fixes.py tests/test_candidate_quality.py tests/test_ui_reorganization.py tests/test_swing_features.py -q`: **78 passed**, 2 cảnh báo protobuf. Các test này chưa bảo vệ những tình huống bên dưới.
- AppTest gọi `render_setup_detail_modal` với candidate mới và chưa có decision: tái hiện `AttributeError: 'NoneType' object has no attribute 'get'` ở dòng 747. Khi có repo nhưng query trả danh sách rỗng, cùng đường lỗi xảy ra.
- Fixture outcomes trong bộ nhớ, không dùng dữ liệu thị trường thật, tái hiện ghép sai ngày và dùng giá khớp tương lai cho kết quả trước ngày khớp.
- Tra cứu toàn bộ Python trong repo: `evaluate_shortlist_and_decision_outcomes` chỉ có định nghĩa và test; chưa có caller trong app hoặc jobs. Vì vậy **vòng đo kết quả shortlist chưa hoạt động trên ứng dụng**, dù đã có hàm.
- Không chạy UI bằng browser, không chạy pipeline mạng hoặc sửa database thật.

| Luồng | Hợp đồng chính | Time / Space | Trạng thái |
|---|---|---|---|
| Chi tiết setup/nhật ký | Chưa có decision vẫn phải mở được form | Toàn renderer chưa định lượng; khối form O(1) | AppTest tái hiện lỗi |
| Hiển thị frozen shortlist | Đúng snapshot, policy và setup; giữ bằng chứng gốc | Với n candidates, f frozen rows: O(n log n + f), bộ nhớ O(n+f), chưa tính DB | Đọc caller/callee và persistence |
| Sizing/kế hoạch | Risk hiển thị bằng số cổ phiếu × khoảng entry-stop đã nhập | O(1) / O(1) cho calculator | Phân tích đường input → display → save |
| Shortlist outcomes | Decision đúng phiên; fill outcome lấy mốc ngày fill | Với n items, b bars, d decisions, h horizons: O(b log b + n(b+h) + d), bộ nhớ phụ O(b+d), output O(nh) | Fixture nhỏ tái hiện; chưa benchmark |

### Cần xác minh

Hiệu quả các ngưỡng breadth và policy theo playbook vẫn cần dữ liệu forward; không xem thiếu bằng chứng lợi nhuận là bug lập trình. Theme và lịch sử luận điểm chưa được audit sâu trong lượt này. Các giới hạn vốn hiện dùng cảnh báo thay vì tự giảm số cổ phiếu; đây là khác biệt với handoff cần chốt rõ trước nghiệm thu sizing, nhưng không tính thành lỗi riêng trong báo cáo này.

## Phần 2: Phân tích kỹ thuật chuyên sâu từng lỗi

### [x] LOGIC-001 — Candidate chưa có decision làm form lỗi ngay lần đầu

- Vị trí: `render_setup_detail_modal`, dòng 712–747. Mức độ Cao; đã sửa & xác nhận.
- Đã sửa: Khởi tạo an toàn `existing_dec = {}` khi repo trả về rỗng hoặc None, loại bỏ hoàn toàn `AttributeError` khi đọc `.get()`.
- Nghiệm thu: Test `test_logic_001_candidate_without_decision_modal_safe` pass (83/83 passed). Mở mã mới, repo rỗng, hoặc chưa có decision đều an toàn và lưu được decision đầu tiên.

### [x] LOGIC-002 — Shortlist đóng băng bị trộn theo ngày và chỉ ghép symbol

- Vị trí: `render_candidates_section`, dòng 657–670. Mức độ Cao; đã sửa & xác nhận.
- Đã sửa: Truyền chính xác `snapshot_id` và `policy_version` khi truy vấn shortlist; sử dụng khóa ghép `(symbol, group_type, setup_type)` để không lẫn các setup của cùng 1 mã; overlay trường bằng chứng gốc từ snapshot thay vì lấy giá trị tính lại; lưu bảng metadata `frozen_shortlist_metadata` để phân biệt snapshot đóng băng 0 mã với snapshot chưa đóng băng.
- Nghiệm thu: Test `test_logic_002_frozen_shortlist_scoped_and_multi_setup` pass. Snapshots cùng ngày không lẫn mã, freeze rỗng vẫn hiển thị 0.

### [x] LOGIC-003 — Sửa entry/stop/size nhưng risk vẫn tính từ candidate gốc

- Vị trí: `render_setup_detail_modal` và `analytics/candidate_quality.py:calculate_trade_plan`. Mức độ Cao; đã sửa & xác nhận.
- Đã sửa: Thống nhất nguồn dữ liệu giữa calculator và form; hỗ trợ tham số `shares` trong `calculate_trade_plan` để tính toán chính xác số tiền rủi ro và tỷ lệ rủi ro tài khoản theo khối lượng nhập; kiểm tra và báo lỗi/cảnh báo nếu mức dừng lỗ sai chiều hoặc rủi ro thực tế vượt ngân sách khi submit form.
- Nghiệm thu: Test `test_logic_003_trade_plan_recalculation_and_risk_validation` pass. Thay đổi stop hay shares cập nhật đúng rủi ro và kích hoạt cảnh báo vượt ngân sách.

### [x] LOGIC-004 — Outcomes ghép decision bằng symbol làm lẫn các phiên

- Vị trí: `analytics/signal_outcomes.py:692–720`. Mức độ Trung bình; đã sửa & xác nhận.
- Đã sửa: Ghép decision theo phạm vi khóa `(session_date, symbol)` và `(snapshot_id, symbol)`, phân biệt rạch ròi quyết định giữa các phiên khác nhau của cùng 1 mã cổ phiếu, không bị ghi đè theo thứ tự mảng.
- Nghiệm thu: Test `test_logic_004_decision_matching_preserves_session_cohorts` pass. Cùng mã ở các ngày khác nhau giữ đúng quyết định độc lập.

### [x] LOGIC-005 — Giá fill ngày sau được dùng tính lợi suất ngày trước

- Vị trí: `analytics/signal_outcomes.py:757–830` và tích hợp `app/components/signal_performance.py`. Mức độ Trung bình; đã sửa & xác nhận.
- Đã sửa: Tách rời `benchmark_returns` (tính từ T+1 Open theo ngày phát hiện tín hiệu) và `fill_returns` (tính theo ngày khớp `actual_fill_date` và giá khớp `actual_fill_price`). Nếu thiếu hoặc sai ngày khớp thì đánh dấu `fill_status` rõ ràng thay vì tính lùi ngày. Tích hợp trực tiếp màn hình Khảo sát Quyết định & Shortlist trong tab Hiệu quả tín hiệu.
- Nghiệm thu: Test `test_logic_005_actual_fill_returns_decoupled_from_signal_date` pass. Return của lệnh khớp luôn tính từ ngày khớp trở đi.

### Thứ tự xử lý

1. LOGIC-001: Đã hoàn tất và xác minh.
2. LOGIC-002 và LOGIC-003: Đã hoàn tất và xác minh.
3. LOGIC-004 và LOGIC-005: Đã hoàn tất, tích hợp UI và xác minh qua toàn bộ bộ test suite (83 passed).

Không cần làm lại toàn bộ thiết kế hoặc sửa các lỗi nhỏ để hoàn thành vòng này.
