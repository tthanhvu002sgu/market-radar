# Domain framing: Market → Groups → Leadership → Setup → Risk → Entry & repeat

Ngày review: 27/09/2026. Route: REVIEW, theo skill frame-domain-problem.

> **Cập nhật sau các vòng sửa ngày 27/09/2026:** Gap report bên dưới là ảnh chụp trạng thái lúc lập tài liệu. D-1 đã có nhãn bối cảnh trên ứng viên; D-2 đã có form luận điểm nhóm và bảng theme; D-3 đã có phiếu kế hoạch; D-4 đã có frozen shortlist, nhật ký quyết định và bảng kết quả riêng; D-5 đã có thống kê chất lượng theo playbook. Hai lỗi lọc shortlist và đếm trùng fill nêu trong báo cáo vòng 2 đã sửa. Phần còn cần làm được tổng hợp ở [mục 10](#10-hướng-đi-tiếp-theo-sau-các-vòng-sửa).

## Gap report

### [D-1] Bối cảnh chưa trở thành đầu vào quyết định ưu tiên

- Severity: High.
- Vì sao cần sửa: người dùng đã xem breadth xấu nhưng shortlist vẫn không giải thích setup thuận hay nghịch bối cảnh đó.
- Evidence: `analytics/screening_rules.py:53` nhận dữ liệu cổ phiếu, ngành và nhóm ngành; không nhận market context tổng hợp. `jobs/update_pipeline.py:288` tính market metrics, nhưng các lời gọi scanner ở 344/356 không truyền chúng. RS vs SPY là so sánh hiệu suất, chưa thay thế trạng thái thị trường.
- Repair: lưu market context theo phiên, đưa nhãn phù hợp/mâu thuẫn/chưa đủ dữ liệu vào từng setup. Ban đầu dùng hỗ trợ rà soát; chỉ dùng làm bộ lọc cứng sau kiểm định.
- Loại gap: thiếu hành vi liên kết; dữ liệu nền đã có.

### [D-2] Groups đã có, Themes và lịch sử lý do lựa chọn còn thiếu

- Severity: Medium.
- Evidence: `analytics/industry_ranker.py:33` xếp GICS sub-industry; `analytics/screening_rules.py:318` gắn điểm nhóm và bonus leader. Đã có chuyển từ ngành/nhóm sang ứng viên qua `app/components/sector_table.py:484` và `app/components/industry_heatmap.py:347`.
- Vì sao cần sửa: phân loại ngành không biểu diễn hết một chủ đề xuyên ngành; lựa chọn nhóm hiện nằm ở bộ lọc UI, chưa thành hồ sơ luận điểm được lưu.
- Repair: trước hết giữ nhóm được chọn và lý do chọn trong cùng phiên rà soát. Theme là phần mở rộng tùy chọn, mỗi quan hệ symbol-theme phải có nguồn, ngày hiệu lực và người xác nhận.
- Loại gap: một phần đã nối ở UI; thiếu mô hình theme và lịch sử lựa chọn. Ảnh viết groups/themes nên thiếu theme không tự động khiến toàn workflow thất bại.

### [D-3] Risk mới ở mức từng setup

- Severity: High nếu mục tiêu bao gồm chuẩn bị giao dịch.
- Evidence: `analytics/candidate_quality.py:37` đo khoảng đến vô hiệu và room/risk; `analytics/setup_analyzer.py:5` xác định rõ không sizing hoặc quản lý sổ lệnh. `select_shortlist` chỉ giới hạn số mã mỗi nhóm.
- Vì sao cần sửa: risk 6% ở đây là khoảng giá so với entry tham chiếu, không phải mất 6% tài khoản. Hai mã mỗi ngành không đo tổng tiền chịu rủi ro hoặc tương quan vị thế.
- Repair: phiếu kế hoạch có vốn, ngân sách rủi ro do người dùng chọn, số cổ phiếu dự kiến, exposure hiện có và giới hạn vốn. Không tự gán mức rủi ro phù hợp cho tài khoản.
- Loại gap: thiếu hành vi ngoài phạm vi radar ban đầu; cần bổ sung nếu muốn hoàn tất chuỗi trong ảnh.

### [D-4] Entry & repeat chưa khép kín với shortlist

- Severity: High.
- Evidence: `jobs/update_pipeline.py:423` gửi `final_candidates` vào signal streaks; `analytics/signal_outcomes.py:119` dùng Open phiên kế tiếp đo forward returns. Schema `storage/database.py:153` lưu signal, không có sổ quyết định chọn/bỏ qua, kế hoạch và fill thực. `analytics/candidate_quality.py:122` đánh giá lại theo policy hiện tại khi hiển thị.
- Vì sao cần sửa: kết quả scanner gốc không trả lời shortlist lúc đó có giúp chọn tốt hơn không; Open ngày sau không chứng minh vào được ở trigger.
- Repair: đóng băng shortlist thực tế với version và snapshot, lưu quyết định chọn/chờ/bỏ qua, theo dõi riêng outcome của tập này. Kế hoạch, trigger quan sát được và fill do người dùng ghi nhận phải là các trường khác nhau.
- Loại gap: đã có vòng lặp đo scanner; thiếu vòng lặp quyết định của người dùng.

### [D-5] Chính sách chất lượng chung chưa chứng minh phù hợp từng playbook

- Severity: Medium.
- Evidence: `QualityPolicy` dùng cùng ngưỡng risk/extension/room cho bốn nhóm; `evaluate_quality` đưa setup không có cản phía trước vào chờ. `rank_for_review` ưu tiên room/risk, rồi risk ATR, sau đó mới score RS.
- Vì sao cần sửa: breakout ở đỉnh mới có thể chưa có cản quan sát được; khung tìm leader và thứ tự ưu tiên cuối cùng hiện không đồng nhất hoàn toàn. Đây là lựa chọn mô hình cần kiểm định, chưa đủ cơ sở gọi là bug.
- Repair: báo tỷ lệ đạt/chờ/loại và lý do theo từng playbook; xác minh mốc cản và vị trí giá trước khi thay ngưỡng. Không dựng target tùy ý để làm đẹp room/risk, không nới ngưỡng để ép có mã.

## 1. Executive frame

- User outcome: đánh giá app có đi theo chuỗi trong ảnh và xác định phần cần cải thiện.
- Audience: người tự rà soát cổ phiếu S&P 500 để swing trade.
- Recommended fidelity: Operational cho phân tích EOD và chuẩn bị kế hoạch do người dùng kiểm tra. Nếu chuyển sang quyết định sizing/đặt lệnh tự động, cần nâng lên high-stakes và thẩm định chuyên môn.
- Primary domain: workflow phân tích thị trường và chọn setup. Secondary: dữ liệu tài chính, đo kết quả, UX và quản trị rủi ro.
- Verdict: **READY WITH ASSUMPTIONS** cho hướng nâng cấp hỗ trợ rà soát. Chưa đủ căn cứ coi app là hệ thống giao dịch có lợi thế đã kiểm chứng.
- Kết luận: đúng hướng về các khối chức năng; mức liên kết và vòng phản hồi còn thiếu. Cần nối logic, trạng thái và bằng chứng giữa các bước.

| Bước | Đã xác nhận trong code | Khoảng thiếu chính |
|---|---|---|
| Market/environment | Breadth, SPY/RSP, A/D, xu hướng, độ tươi và lịch phiên | Context dùng chung và cách setup phản ứng với context |
| Groups/themes | Sector rotation, GICS sub-industry COMP/BLEND, breadth/median, drill-down | Luận điểm chọn nhóm được lưu; theme tùy chọn |
| Leadership/RS | RS vs SPY/ngành, RS percentile nhiều kỳ, điều kiện leader và bonus | Độ bền leadership, diễn biến thứ hạng và giải trình thống nhất |
| Setup | Bốn nhóm swing, base lifecycle, trigger/vô hiệu, checklist OHLC/volume | Policy phù hợp từng playbook, kiểm định các nhãn và ngưỡng |
| Risk | Risk %/ATR, room/risk, thanh khoản, earnings, cap nhóm | Sizing theo tài khoản và tổng exposure |
| Entry & repeat | Link TradingView, CSV, snapshot, events, streaks, forward outcomes | Kế hoạch, quyết định thực, fill và review đúng shortlist |

## 2. What an expert sees

1. Phân biệt sức mạnh tương đối và tăng giá tuyệt đối: giảm ít hơn SPY vẫn có thể là RS dương. RS comparison là quan hệ hiệu suất với benchmark, theo [Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/relative-strength-comparison). App hiện dùng chênh lệch lợi suất 20 phiên; chỉ số 1–99 là percentile nội bộ, không phải bản sao RS Rating thương mại.
2. Một nhóm chỉ có 1–2 thành viên S&P 500 không đại diện đầy đủ ngành. Code đã có cờ mẫu nhỏ; cần giữ cờ xuyên suốt tới shortlist.
3. Setup hình thành, đã xác nhận EOD và còn điểm vào hợp lý là ba câu hỏi khác nhau. Gate chống mua đuổi hiện có là nền tốt.
4. Dữ liệu EOD và chart intraday phải có thời điểm riêng; không lấy giá hôm nay để giải thích quyết định quá khứ.
5. Khoảng vô hiệu là risk tham chiếu. Giá stop không bảo đảm giá khớp trong biến động mạnh, theo [FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets).
6. Repeat cần biết đã chọn gì, đã bỏ gì và vì sao. Điểm scanner hoặc forward gross return không tự chứng minh lợi nhuận thực.

Các kết quả dễ gây hiểu sai: heatmap toàn màu xanh với mẫu nhỏ; leader mạnh nhưng quá xa điểm vào; shortlist rỗng vì thiếu dữ liệu được diễn giải thành thị trường không có cơ hội; performance của scanner được gán cho shortlist. Sai số lớn đến từ coverage, corporate actions, lịch earnings ước tính, ngưỡng heuristic và giả định khớp lệnh.

## 3. Minimum domain model

### Boundary and entities

Trong phạm vi: universe S&P 500, market snapshot, group, symbol, setup, review decision và outcome. Mở rộng có giới hạn: kế hoạch thủ công và danh sách vị thế do người dùng nhập. Broker execution, dữ liệu tick và dự báo lợi nhuận nằm ngoài giai đoạn đầu.

### State / process

Snapshot hợp lệ → rà soát bối cảnh → chọn nhóm → kiểm tra leader → setup đạt/chờ/loại → lưu quyết định. Nhánh kế hoạch tùy chọn: draft → chờ trigger → người dùng ghi nhận đã vào / hủy / hết hạn → đã đóng → review.

Trạng thái scanner, quality tier và trạng thái kế hoạch độc lập. “Confirmed” của scanner không tự chuyển kế hoạch thành “đã vào”. Mỗi bước được phép kết thúc bằng không hành động.

### Governing logic

- Giữ RS vs SPY/ngành và percentile nội bộ với tên, kỳ tính và mẫu so sánh rõ ràng.
- Context có xu hướng, độ rộng, biến động và chất lượng dữ liệu; chưa gộp thành điểm xác suất thắng. Nhãn phù hợp setup cần version và lý do.
- Công thức hiện có: `entry_ref = max(close, trigger)` cho long, `min(close, trigger)` cho short; `risk = side × (entry_ref − invalidation)`; `room = side × (barrier − entry_ref)`, với side = +1/-1.
- Chỉ tính room/risk nếu cả hai dương. Không có cản thì giá trị chưa biết.
- Sizing đề xuất cho cổ phiếu nguyên đơn vị: `q = floor(min(B/d, capital_cap/entry))`, B là ngân sách tiền chịu rủi ro do người dùng nhập, d là khoảng entry-stop dương. Kiểm tra thêm phí/slippage, số dư và tổng vị thế; đây là ước tính theo kế hoạch, không bảo đảm mức lỗ tối đa khi gap.
- Không mặc định B hoặc tự cho phép short khi chưa biết điều kiện vay.

### Inputs

| Input | Ý nghĩa | Type/unit | Range/default | Source | Confidence |
|---|---|---|---|---|---|
| OHLCV, as_of | Giá và phiên quan sát | USD, shares, session | Giá >0, volume ≥0; thiếu → unknown | Provider/snapshot | Cần kiểm coverage và điều chỉnh giá |
| SPY/RSP/ngành | Benchmark đúng kỳ | % và USD | Cùng lịch phiên | Snapshot | Quan sát có điều kiện chất lượng |
| Membership | Thành viên nhóm tại thời điểm | ID, ngày hiệu lực | GICS hiện có; theme chưa mặc định | Constituents; mapping bổ sung | Lịch sử membership cần xác minh trước backtest |
| ATR, trigger, stop, barrier | Cấu trúc setup | USD, ATR multiple | Dương; stop đúng chiều | Setup analyzer | Quan sát + heuristic |
| Earnings | Sự kiện gần nhất sắp tới | Date, ngày lịch | Thiếu/ước tính phải gắn nhãn | FA snapshot | Ước tính |
| Equity, budget, positions | Ràng buộc tài khoản | USD, shares | Không có default rủi ro; thiếu → chưa sizing | Người dùng | Phụ thuộc nhập liệu |
| Decision/version | Quyết định tại thời điểm | Enum, ID, timestamp | Lưu bất biến bản gốc | App/người dùng | Kiểm tra truy vết |

### Outputs

| Output | Ý nghĩa | Type/unit | Validation |
|---|---|---|---|
| Context và suitability | Bằng chứng thuận/nghịch setup | Enum + reasons | Truy về snapshot; trường hợp unknown |
| Shortlist | Danh sách ưu tiên để xem chart | IDs, ranks, version | Deterministic, không ép đủ mã |
| Plan | Entry/stop/size dự kiến | USD, shares | Tính lại độc lập, kiểm giới hạn |
| Review | Kết quả theo tập đã lưu | %, R nếu có risk gốc, số quan sát | Cohort/version rõ; chi phí và fill rõ |

### Constraints, edge cases, and misuse

EOD không xác nhận fill intraday. Khi cùng bar chạm entry và stop, thứ tự có thể không biết. Thiếu benchmark/earnings/membership không suy thành trung tính hoặc an toàn. Lịch tuần chưa đóng, cổ phiếu mới, split, gap, short borrow và dữ liệu cũ cần đường xử lý rõ. Cần timezone ET/ICT và phiên tham chiếu. Margin/settlement không áp dụng giai đoạn rà soát; phải mô hình hóa nếu sau này kiểm sức mua hoặc execution.

## 4. Evidence and uncertainty ledger

| Claim/decision | Class | Evidence | Impact if wrong | Validation/owner |
|---|---|---|---|---|
| Chuỗi trong ảnh là chuẩn so sánh | User fact | Ảnh người dùng | Lệch mục tiêu | Người dùng |
| App đã có group → candidate drill-down | Verified fact | sector_table/industry_heatmap | Đề xuất làm lại thừa | Code + regression |
| Context chưa vào scanner như đầu vào tổng hợp | Verified fact | Pipeline và signature scanner | Nhận định sai liên kết | Maintainer |
| Outcomes đo scanner gốc | Verified fact | Pipeline, signal_outcomes | Gán sai hiệu quả | Maintainer |
| Giữ phạm vi S&P 500/EOD | Assumption | README hiện tại | Thiếu universe mong muốn | Người dùng xác nhận nếu đổi phạm vi |
| Context giúp ưu tiên tốt hơn | Proposal | Chưa có bằng chứng lợi nhuận trong review | Loại nhầm cơ hội | So sánh forward, người dùng + reviewer định lượng |
| Sizing thủ công đủ cho bước đầu | Assumption | Mục tiêu mở rộng workflow | Thiếu account constraints | Rà soát công thức và nhu cầu trước bật |

Ảnh là nội dung tham chiếu, không phải lệnh sửa code. Các nguồn Fidelity/FINRA hỗ trợ định nghĩa RS và rủi ro stop, không chứng minh chuỗi này hoặc bộ ngưỡng hiện có tạo lợi nhuận.

## 5. Feature map

### Core

- P0 — Trang tổng hợp theo chuỗi sáu bước, giữ snapshot/nhóm/ứng viên đã chọn: đáp ứng yêu cầu người dùng theo được một luận điểm liên tục.
- P0 — Market context và suitability có lý do trên candidate: nối phân tích thị trường với rà soát setup, ban đầu không tự chặn giao dịch.
- P0 — Lưu shortlist và quyết định với version ngay từ đầu: tạo mẫu đúng cho vòng repeat.
- P1 — Phiếu kế hoạch và kiểm tra risk theo tài khoản, người dùng nhập các ràng buộc: hoàn tất bước chuẩn bị trước entry.
- P1 — Review riêng scanner, shortlist và quyết định thực: trả lời đúng lớp nào giúp ích.

### Trust

Hiện as_of/coverage/version ở mỗi bước; chỉ rõ thiếu dữ liệu, số thành viên nhóm, công thức RS và ngưỡng heuristic. Giữ nguyên policy khi xem lại quyết định gốc; chế độ tính lại phải ghi là đánh giá lại.

### Explore

Theo dõi độ bền leader; so sánh context có/không, theo playbook, theo kỳ giữ; báo tỷ lệ pass/wait/reject và nguyên nhân. Đo thời gian rà soát bên cạnh kết quả giá.

### Later / out of scope

Theme xuyên ngành với nguồn kiểm chứng; mở rộng toàn thị trường; tin vĩ mô; broker integration; tự động sizing/đặt lệnh; tối ưu ngưỡng theo lợi nhuận. Không cần các phần này để sửa liên kết cơ bản.

## 6. Acceptance and validation

- Đã chạy `python -m pytest tests/test_candidate_quality.py tests/test_ui_reorganization.py tests/test_swing_features.py -q`: **62 passed**, 2 cảnh báo deprecation protobuf. Đây là kiểm tra hành vi hiện có; không chứng minh edge.
- Review dựa vào source, tài liệu và test, chưa quan sát phiên UI chạy thật hoặc kiểm toán lại toàn bộ database. Không dùng số mẫu của review 17/09 như số liệu hiện tại.
- Reference cases cần có khi triển khai: thị trường/nhóm/leader đồng thuận; RS dương nhưng giá giảm; nhóm mẫu nhỏ; thiếu benchmark; breakout không có cản; trigger quá xa; không có candidate; trùng theme; plan hết hạn; gap vượt stop.
- Cùng snapshot và version phải tái tạo đúng 100% danh sách/decision evidence. USD hiển thị 2 số lẻ nhưng tính nội bộ không làm tròn sớm; số cổ phiếu nguyên và không vượt ngân sách kế hoạch trong giả định chi phí đã nêu.
- Test workflow: đổi snapshot không giữ nhầm quyết định ở phiên khác; quay lại candidate giữ đúng nhóm; quality ready không tự tạo fill; bỏ qua vẫn lưu lý do.
- Đánh giá forward theo thời gian: lưu policy trước quan sát kết quả, so scanner và shortlist trên cùng cửa sổ; công bố số mẫu, dữ liệu chưa trưởng thành, uncertainty và chi phí. Không có ngưỡng lợi nhuận nghiệm thu vì chưa có benchmark/độ lớn mẫu được thiết kế.
- Người am hiểu quản trị rủi ro và giao dịch cần rà soát sizing, stop và giả định fill trước khi dùng cho vốn thật. Nếu nâng lên tự động thực thi, cần đánh giá high-stakes riêng.

## 7. Open decisions

Không có câu hỏi chặn bản review. Mặc định đề xuất có thể đảo lại:

1. Mục tiêu: giữ radar EOD + kế hoạch thủ công trước; tự động giao dịch sẽ thay đổi đáng kể kiến trúc và chuẩn kiểm định.
2. Phạm vi groups/themes: dùng GICS hiện có trước; theme chỉ thêm khi có nguồn mapping đáng tin.
3. Mức can thiệp context: hiển thị phù hợp/mâu thuẫn trước; chuyển thành gate cứng sau khi so sánh forward.

## 8. Readiness score

Điểm cho brief nâng cấp hỗ trợ rà soát, không phải tỷ lệ app đã hoàn thiện hoặc xác suất giao dịch thắng.

| Dimension | Score | Gap |
|---|---|---|
| Outcome/audience/fidelity | 2 | Operational, do người dùng quyết định |
| Boundary/entities/state | 2 | Phân biệt scanner/quality/plan |
| Governing logic | 1 | Suitability policy cần thiết kế/kiểm định |
| Inputs/outputs/units | 2 | Có schema tối thiểu, không default risk |
| Constraints/failures | 2 | Unknown, stale, fill, gap đã tách |
| Evidence/assumptions | 1 | Chưa chứng minh lợi ích context/shortlist |
| Validation/tolerances | 1 | Có acceptance kỹ thuật; forward chưa thực hiện |
| MVP/deferred scope | 2 | P0/P1 và Later tách rõ |

Total: **13/16 — READY WITH ASSUMPTIONS** cho P0 hỗ trợ review. P1 cần xác định account constraints và thẩm định trước dùng thực tế. Hành động nhỏ nhất: nối context và lưu quyết định từ bây giờ để có dữ liệu kiểm định.

## 9. Build handoff

- Goal: người dùng giải thích được vì sao chọn một mã qua toàn chuỗi và xem lại kết quả của đúng quyết định đó.
- Required behaviors: tái dùng market/group/setup modules; giữ drill-down hiện có; thêm context giải trình và decision log; cho phép chờ/bỏ qua/không hành động.
- Data contract đề xuất: `snapshot_id`, `as_of`, `universe_version`, `context_version`, `quality_version`, `symbol`, `group_id`, `setup_id`, `decision`, `reason`, `created_at`; quan hệ tới kế hoạch tùy chọn. Lưu bằng chứng/giá trị thực của phiên bản lúc chọn, không chỉ tên version.
- Formula/state contracts: theo mục 3; scanner confirmed, quality ready và trade filled là trạng thái riêng. Mọi sửa kế hoạch tạo revision có timestamp.
- Error behavior: thiếu dữ liệu hiện unknown; dữ liệu cũ hiện độ trễ; thiếu tài khoản không xuất size; không suy fill từ nến EOD.
- Acceptance: theo mục 6, ưu tiên tái lập quyết định và chặn nhầm trạng thái. Chưa đặt mục tiêu nâng win rate.
- Assumptions: S&P 500, EOD, USD, user-in-the-loop; P0 chưa thay scanner/gate hiện tại.
- Deferred: theme tự động, dữ liệu ngoài universe, execution và tối ưu lợi nhuận.

Review này chỉ bổ sung tài liệu; không thay đổi logic hoặc giao diện ứng dụng.

## 10. Hướng đi tiếp theo sau các vòng sửa

Đây là danh sách ưu tiên mới dựa trên code và DB local đọc ngày 27/09/2026. DB có 6 snapshots nhưng chỉ thuộc 2 phiên độc lập (04/09 và 11/09), 0 frozen shortlist và 0 quyết định. Có 2.936 dòng scanner outcomes, trong đó 850 dòng `completed` theo trạng thái lưu. Vì vậy các màn kết quả shortlist mới **chưa có mẫu thực tế** để đánh giá.

| Thứ tự | Việc cần làm | Vì sao | Nghiệm thu tối thiểu |
|---|---|---|---|
| 0 | Chạy lại pipeline trên phiên mới và xem đối chiếu dữ liệu | Chưa có cohort frozen/decision trong DB local; không thể xác minh vòng lặp mới bằng dữ liệu thực | Snapshot mới có as_of/coverage rõ; frozen metadata được lưu kể cả shortlist rỗng; UI hiển thị đúng snapshot |
| 1 | Hoàn thiện hợp đồng kế hoạch/rủi ro | Form hiện đề xuất mặc định 1% ngân sách risk và 20% trần vị thế; calculator cảnh báo vượt trần nhưng vẫn đưa số cổ phiếu tính theo ngân sách risk. Quyết định lưu không chứa vốn/ngân sách/trần đã dùng | Người dùng nhập hoặc xác nhận tham số; risk và exposure tính từ đúng plan được lưu; trần được áp dụng theo chính sách rõ; mở lại plan tái tạo được phép tính; gắn nhãn chi phí và gap |
| 2 | Tạo trang/luồng rà soát theo sáu bước | Các khối hiện nằm trên nhiều trang; trang Tổng hợp phiên là dòng sự kiện, chưa lưu một hồ sơ nối market → group → leader → setup → risk → plan | Chọn một snapshot và nhóm rồi mở ứng viên vẫn giữ bối cảnh; từng bước cho phép ghi “không hành động” và lý do; xem lại đường đi của một quyết định |
| 3 | Lưu lịch sử trạng thái và phiên bản luận điểm | `trade_decisions` và `review_theses` hiện là upsert; cập nhật sẽ ghi đè lý do/trạng thái cũ. Frozen shortlist lưu một phần evidence, không có bản đầy đủ về rule/context/quality của quyết định | Mỗi thay đổi có revision và timestamp; xem lại được đầu vào/rule/version gốc; phân biệt đánh giá gốc với tính lại theo rule mới |
| 4 | Thiết kế đo forward trước khi chỉnh ngưỡng | `review-v1` và nhãn context đang là heuristic; hai phiên độc lập không đủ kiểm tra hiệu quả | Có các cohort scanner/shortlist/decision cùng cửa sổ, số mẫu hoàn tất, pending, cách xử lý thiếu dữ liệu, chi phí giả định, phân rã theo playbook/context; chỉ so sánh trên dữ liệu đến sau lúc khóa rule |

Hai chỉnh sửa nhỏ có ích trong thứ tự trên: màn đánh giá shortlist nên hiển thị dù scanner outcome chưa có (`signal_performance.py` đang return sớm khi thiếu scanner rows); nhãn market context hiện dựa chủ yếu trên tỷ lệ cổ phiếu trên MA50/MA200, nên mô tả đúng đó là tín hiệu độ rộng, tránh câu chữ ngầm dự báo xác suất hoặc dòng tiền.

**Chưa ưu tiên:** tự động gán theme, thêm chỉ báo/điểm tổng hợp, siết context thành gate cứng, mở rộng universe, tích hợp broker hoặc tối ưu tham số. Bảng theme trong DB đã có nhưng chưa có luồng nhập/sửa trong UI; chỉ triển khai nếu người dùng thực sự cần chủ đề xuyên ngành.

## 11. Đã nối luồng rà soát sáu bước

Trang **Luồng rà soát** nằm trong nhóm Quy trình rà soát và mở được từ trang Thị trường hoặc Tổng hợp phiên. Trước đây người dùng phải đi qua các trang Thị trường, Ngành/Nhóm ngành, Ứng viên và modal setup riêng; trạng thái nhóm/mã không tạo thành một lượt rà soát. Nay cùng một trang đi theo thứ tự thị trường → nhóm → leadership/RS → setup → risk → entry & repeat. Các trang cũ vẫn là màn chi tiết; nút quay lại giữ snapshot, ngành/nhóm và mã đã chọn. Đổi snapshot xóa lựa chọn của lượt cũ.

| Bước | Trên luồng | Màn chi tiết hiện có |
|---|---|---|
| Market/environment | Độ rộng, coverage, cảnh báo dữ liệu | Thị trường |
| Groups/themes | Ngành GICS, nhóm ngành, hạng và quy mô; theme xác minh của mã nếu có | Ngành, Nhóm ngành |
| Leadership/RS | Chọn đúng setup của mã, leader, RS rating và RS 20 phiên so SPY | Ứng viên |
| Setup | Trigger, mức vô hiệu, trạng thái | Modal chi tiết setup |
| Risk | Tier/chứng cứ quality và rủi ro theo giá/ATR/khoảng trống | Modal kế hoạch/rủi ro |
| Entry & repeat | Quyết định đã lưu cho đúng snapshot, mở phiếu kế hoạch, ghi nhận lượt rà soát, xem kết quả | Modal quyết định, Chất lượng tín hiệu |

Lượt rà soát lưu append-only trong `workflow_reviews`: snapshot, đường đi, kết luận tiếp tục/chờ/không hành động, bước dừng, lý do và bằng chứng số liệu đã xem. Lịch sử của snapshot hiển thị lại đường đi và evidence gốc. Nó là nhật ký rà soát; `trade_decisions` vẫn là phiếu quyết định/entry riêng. RS rating chỉ có ở snapshot mới; với snapshot cũ, luồng tính lại chênh lệch lợi suất 20 phiên từ ứng viên và SPY của cùng snapshot khi đủ dữ liệu, còn thiếu thì ghi N/A.

Phần chưa hoàn thành của hướng đi tổng thể: lưu revision đầy đủ cho phiếu kế hoạch/quyết định, persistence của vốn và budget rủi ro, cùng đo forward trên nhiều phiên. Luồng này không suy ra giao dịch đã khớp từ tín hiệu EOD.

### Menu sau khi sắp lại

**Thị trường** là trang mở mặc định và mục đầu tiên của sidebar. Nhóm **Quy trình rà soát** đi theo thứ tự Thị trường → Ngành → Nhóm ngành → Ứng viên → Nền giá & bứt phá → Rà soát 6 bước → Chất lượng tín hiệu. **Phiên & sự kiện** giữ Tổng hợp phiên, Lịch BCTC và Thay đổi giữa phiên; **Hệ thống** giữ Dữ liệu & vận hành. Tên route nội bộ không đổi nên các lối đi từ sự kiện, heatmap và ứng viên vẫn hoạt động.
