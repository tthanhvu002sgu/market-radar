# Tái kiểm tra gap fixes — vòng 2

## Phần 1: Bảng tổng hợp rủi ro logic

Phạm vi: các bản sửa sau báo cáo `gap-fixes-recheck-2026-09-27.md`, tập trung luồng shortlist, chi tiết kế hoạch và outcomes. Checkout vẫn có thay đổi chưa commit. Không sửa code sản phẩm. Theo yêu cầu người dùng, chỉ giữ vấn đề có tác động đáng kể; không báo lỗi trình bày hoặc các đề xuất mở rộng.

**Kết luận: đã sửa được các ca cũ quan trọng, còn hai lỗi cần xử lý trước khi nghiệm thu luồng lọc và thống kê.**

- LOGIC-001: AppTest mở candidate mới không có decision trả `NEW_DECISION_ERRORS []`; lỗi None đã sửa.
- LOGIC-002: đã truyền snapshot/policy, thêm metadata cho shortlist rỗng và giới hạn 10. Tuy nhiên khâu ghép frozen gây regression ở LOGIC-006 bên dưới.
- LOGIC-003: calculator nhận shares thực; submit tính lại từ form và cảnh báo vượt ngân sách; stop sai chiều bị chặn. Chưa xem việc này là chứng nhận toàn bộ quản trị rủi ro tài khoản.
- LOGIC-004: ghép decision theo ngày đã sửa ca cùng mã khác ngày. Ca nhiều snapshots cùng ngày còn sai ở LOGIC-007.
- LOGIC-005: benchmark và fill returns tách riêng; fill horizon lấy từ ngày fill. Test ca vào muộn đã qua.
- Evaluator mới đã có caller trong `app/components/signal_performance.py`.

| ID | Vị trí | Loại lỗi | Mức độ | Tác động thực tế | Bằng chứng |
|---|---|---|---|---|---|
| LOGIC-006 | `app/components/candidate_cards.py:697–722` | Ghép dữ liệu bỏ qua bộ lọc | Cao | Tìm một mã hoặc đi từ nhóm ngành vẫn hiện mã ngoài điều kiện | Đã xác nhận bằng tái hiện AppTest |
| LOGIC-007 | `app/components/signal_performance.py:318`, `analytics/signal_outcomes.py:733` | Lặp mẫu và gán decision sai snapshot | Cao | Một quyết định/khớp lệnh được đếm nhiều lần, làm sai thống kê | Đã xác nhận bằng tái hiện evaluator và phân tích caller |

### Kiểm chứng và độ bao phủ

Lệnh: `python -m pytest tests/test_gap_fixes.py tests/test_candidate_quality.py tests/test_ui_reorganization.py tests/test_swing_features.py -q` → **83 passed**, 2 cảnh báo protobuf.

AppTest dùng fixture trong bộ nhớ. Để quan sát tập sau xử lý, ca shortlist thay hàm vẽ bảng bằng bộ ghi danh sách symbol; toàn bộ logic lọc và ghép của `render_candidates_section` chạy nguyên trạng. Không dùng/sửa database thật. Ca mở setup dùng renderer thật. Không kiểm thử toàn bộ browser hoặc pipeline mạng.

| Luồng | Precondition → invariant → postcondition | Time / Space | Kiểm chứng |
|---|---|---|---|
| Frozen shortlist | Có frozen snapshot và bộ lọc UI → chỉ giữ rows thỏa điều kiện → bảng/CSV đúng tập đã chọn | O(n log n + f log f), bộ nhớ O(n+f), ngoài I/O DB | AppTest tái hiện; n candidates, f frozen rows |
| Decision outcomes | Nhiều snapshot cùng phiên → mỗi decision/fill có danh tính duy nhất → số mẫu không tăng theo số lần refresh | Evaluator O(b log b + n(b+h) + d), bộ nhớ phụ O(b+d), output O(nh) | Fixture tái hiện; b bars, n rows, h horizons, d decisions |

### Cần xác minh

Chưa đánh giá lợi thế tài chính của policy. Báo cáo này xác nhận hành vi kỹ thuật được kiểm tra, không bảo đảm toàn bộ app. Hợp đồng thống kê cần chỉ rõ đơn vị mẫu: quyết định, symbol/phiên, hay từng phiên bản shortlist; số lệnh khớp phải đếm theo sự kiện fill thực, không theo số bản chụp.

## Phần 2: Phân tích kỹ thuật chuyên sâu từng lỗi

### [ ] LOGIC-006 — Frozen rows bị loại bởi filter được thêm ngược trở lại

- **Vị trí/mức độ:** `render_candidates_section`, dòng 697–722; Cao; đã tái hiện.
- **Mã liên quan:**

```python
if matched_c:
    merged = dict(matched_c)
else:
    merged = dict(f)
```

```python
matched_shortlist.append(merged)
```

- **Nguyên nhân:** `display_candidates` đã được lọc theo nhóm/ngành/tìm kiếm. Sau đó vòng lặp duyệt tất cả frozen rows; khi row không còn trong tập đã lọc, nhánh `else` dựng lại row từ frozen và thêm vào kết quả. Như vậy dữ liệu bị loại được phục hồi. Fallback theo symbol cũng có thể thay setup đã đóng băng bằng setup khác cùng mã.
- **Ca đã chạy:** frozen có AAA và BBB. AppTest đặt `cand_search_input = 'AAA'`. Kỳ vọng chỉ AAA; thực tế `FILTER_RESULT ['{"rendered_symbols": ["AAA", "BBB"]}']`, không có exception. Đây cũng là đường gây sai drill-down nhóm ngành vì các filter được áp dụng trước khâu ghép.
- **Sửa:** dựng tập frozen hoàn chỉnh bằng khóa snapshot/policy/symbol/group/setup trước, rồi áp dụng các filter UI lên tập này. Không fallback sang setup khác. Với row thiếu dữ liệu nguồn, hiện rõ thiếu dữ liệu, không dùng việc thiếu match để bỏ qua bộ lọc.
- **Nghiệm thu:** tìm AAA chỉ hiện AAA; tìm mã không tồn tại trả 0; lọc ngành không lẫn ngành khác; bảng/CSV cùng tập; không bật filter vẫn đúng danh sách frozen.

### [ ] LOGIC-007 — Một fill bị đếm hai lần khi có hai snapshot cùng ngày

- **Vị trí/mức độ:** caller `signal_performance.py:318–330`, evaluator `signal_outcomes.py:727–734`; Cao; đã tái hiện.
- **Mã liên quan:**

```python
frozen_all = repo.get_frozen_shortlist() if (repo and hasattr(repo, "get_frozen_shortlist")) else []
```

```python
elif session_d and (session_d, sym) in decisions_by_date_sym:
    dec = decisions_by_date_sym[(session_d, sym)]
```

- **Nguyên nhân:** màn đánh giá lấy tất cả frozen snapshots, không chọn cohort hoặc loại bản chụp lặp. Khi snapshot của một row không khớp decision, evaluator tiếp tục fallback theo ngày+symbol, dù decision đã có snapshot_id khác. Cùng một decision/fill vì thế gắn vào nhiều rows. Pipeline chạy lại trong cùng phiên tạo snapshot mới là đường sử dụng bình thường.
- **Ca đã chạy:** shortlist AAA ngày 01/09 có snapshot 1 và 2. Chỉ một decision `chon`, `snapshot_id=2`, fill ngày 04/09 tại 120. Evaluator trả nhóm `chon` với `count=2`, `fill_count=2`; cả hai dùng fill return 1d=8,33%. Kỳ vọng một fill thực; row snapshot 1 không được nhận decision của snapshot 2.
- **Tác động:** số lệnh khớp bị phóng đại; mẫu nào xuất hiện qua nhiều lần refresh có trọng số lớn hơn. Khi mức lặp khác nhau giữa các mã/phiên, trung bình return và slippage cũng bị lệch.
- **Sửa:** khi hai bên có snapshot_id thì phải khớp chính xác; chỉ dùng fallback cho dữ liệu cũ thật sự không có ID, với quy tắc migration rõ. Chọn cohort/version cho thống kê, hoặc tách đánh giá snapshot khỏi thống kê decision/fill; mỗi decision/fill thực chỉ góp một mẫu trong bảng tương ứng.
- **Nghiệm thu:** thêm snapshot lặp không tăng số fill hoặc đổi thống kê của quyết định thực; decision snapshot 2 không áp lên snapshot 1; đảo thứ tự input không đổi kết quả; policy versions không bị trộn âm thầm.

Ưu tiên sửa hai lỗi này. Không cần làm lại các phần đã kiểm chứng ở vòng trước.

## Trạng thái sau sửa

- LOGIC-006: **Đã sửa.** Shortlist đóng băng chỉ ghép với candidate còn trong tập đã lọc và khớp đủ symbol/group/setup. AppTest kiểm tra tìm AAA, tìm mã không tồn tại và lọc ngành.
- LOGIC-007: **Đã sửa.** Evaluator chọn một bản ghi cho mỗi symbol/phiên, ưu tiên snapshot gắn với decision, rồi mới đến snapshot mới nhất. Decision có snapshot_id khác không được ghép bằng ngày; số quyết định trên UI đếm trong cohort đã đánh giá. Test kiểm tra hai snapshot cùng ngày chỉ có một decision/fill, kể cả khi đảo thứ tự input.
- Kiểm chứng sau sửa: `python -m pytest tests/ -q` → **246 passed**, 2 cảnh báo deprecation protobuf; `git diff --check` trên ba file sản phẩm đã sửa không báo lỗi whitespace. Chưa chạy pipeline với dữ liệu thị trường thật.
