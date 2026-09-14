# Review tính năng: Market Radar → công cụ swing trading cổ phiếu

Ngày: 08/09/2026. Route REVIEW theo frame-domain-problem.

Người dùng xác nhận “có phí” là “cổ phiếu”; không có yêu cầu xây sản phẩm thu phí hay mua dữ liệu. Đã rà README mới, schema, repository, analytics, pipeline và UI. Không sửa code, không chạy tải dữ liệu hoặc kiểm thử UI; không coi tuyên bố README “đã sửa toàn bộ” là kết quả tái kiểm định. Báo cáo này tập trung khoảng trống tính năng, không lặp lại audit trước.

## Gap report

| ID | Severity | Khoảng trống và tác động | Bằng chứng hiện trạng | Bổ sung nhỏ nhất |
|---|---|---|---|---|
| F01 | High | Có ứng viên nhưng chưa có kế hoạch giao dịch; người dùng phải tự nối trigger, invalidation, size | screening_rules trả candidate; schema chưa có trade_plan | Trade plan lưu giá kích hoạt, vô hiệu, expiry, hướng, luận điểm |
| F02 | High | Không đánh giá được lệnh mới có làm danh mục tập trung hoặc vượt ngân sách rủi ro | Chưa có account/position/fill trong schema hoặc repository | Vị thế nhập tay/CSV và tính rủi ro trước/sau thêm lệnh |
| F03 | High | Không đo được setup nào thực sự hữu ích hay người dùng thực thi tốt đến đâu | Lịch sử hiện là snapshot/delta, chưa có executions/outcomes | Nhật ký gắn plan và signal snapshot; tách kết quả thật khỏi giả lập |
| F04 | Medium | Tab watchlist hiện là nhóm tín hiệu máy, chưa phải danh sách cá nhân tồn tại qua các phiên | candidate_cards nhóm theo group_type; không có watchlist CRUD | Pin/dismiss/notes/priority, trạng thái và lịch sử setup riêng |
| F05 | Medium | Khó phân biệt mã mạnh với mã có điểm giao dịch phù hợp hôm nay | Indicator chủ yếu daily MA/returns/volume; không thấy ATR, risk distance, weekly context | Setup geometry, weekly context, distance-to-trigger và extension |
| F06 | Medium | Không có nhắc việc theo trạng thái, người dùng phải tự refresh và dò lại | UI gọi pipeline bằng nút; chưa có alert rule/event delivery | Alert EOD có idempotency, expiry, delivery status |
| F07 | Medium | Chưa có đo hiệu quả scanner độc lập với việc người dùng chọn lệnh | Tests/analytics hiện không có signal outcome engine | Forward outcomes và so sánh baseline, theo setup/regime |

Các mức High nói về khoảng trống so với mục tiêu workstation swing hoàn chỉnh, không có nghĩa mọi screener đều phải tự làm broker hoặc journal.

## 1. Executive frame

- Outcome: người dùng có thể đi từ bối cảnh thị trường đến lựa chọn, kế hoạch, giám sát và rút kinh nghiệm giao dịch cổ phiếu.
- Audience: cá nhân swing cổ phiếu, quyết định và đặt lệnh thủ công. Universe hiện S&P500; chưa có yêu cầu mở rộng.
- Fidelity: Operational cho research/watchlist/journal; phần sizing/risk phải đạt mức kiểm chứng cao cho financial action, gồm đối chiếu độc lập trước dùng thật.
- Domain chính: discretionary equity swing workflow. Phụ: market data, quản lý rủi ro, sổ giao dịch, đo lường kết quả và vận hành cảnh báo.
- Verdict: READY WITH ASSUMPTIONS cho lập phạm vi nâng cấp; NOT READY để coi bản hiện tại là workstation quản lý toàn vòng đời và sử dụng sizing tự động. Không có tuyên bố khả năng sinh lời.
- Định vị đề xuất: công cụ chuẩn bị và kiểm soát giao dịch gắn TradingView/broker; phát triển thành một chu trình khép kín theo từng module.

### Những thứ đã có — không cần đề xuất như tính năng mới

Market breadth và SPY/RSP; sector/sub-industry ranking; bốn nhóm ứng viên; setup/triggered trong card; bảng rút gọn và tìm mã/tên; filter leader; score/rank metadata trong schema; FA flags và earnings warning; snapshot/delta và CSV; đường dẫn chart TradingView. Tất cả nhận định này dựa trên code đang đọc, không phải chứng nhận chất lượng hoạt động đầy đủ.

## 2. What an expert sees

1. Mã mạnh, setup đẹp, điểm vào hợp lý và lệnh phù hợp danh mục là bốn đánh giá khác nhau. Một score không nên che lấp chúng.
2. Trigger trên nến EOD chỉ là sự kiện quan sát; không phải đã có fill ở giá breakout. Phiên sau có thể gap vượt vùng được phép mua.
3. Stop là điều kiện/tham chiếu quản trị rủi ro; gap có thể làm lỗ thực tế vượt risk-to-stop.
4. Nhiều cổ phiếu cùng theme có thể là cùng một khoản đặt cược dù khác ticker; tương quan lịch sử cũng có thể thay đổi khi stress.
5. Hệ thống cần hỗ trợ quyết định “bỏ qua”: extended, quá gần earnings, không đủ room, quá tập trung, hoặc chưa rõ dữ liệu.
6. Kết quả scanner, kết quả chiến lược mô phỏng và kết quả trader là ba tập khác nhau. Cần giữ cả ứng viên bị bỏ qua để tránh selection bias trong đánh giá scanner.
7. Tính chuyên nghiệp thể hiện qua quy tắc nhất quán, khả năng truy vết và review, không được suy ra từ nhiều indicator hoặc giao diện đẹp.

Thuật ngữ: setup (cấu trúc đang hình thành), trigger (điều kiện kích hoạt), invalidation (điều kiện làm luận điểm không còn đúng), initial R (ngân sách rủi ro ban đầu được đóng băng), portfolio heat (tổng rủi ro theo stop theo quy ước đã công bố), MAE/MFE (diễn biến bất lợi/thuận lợi tối đa trong khoảng giữ lệnh).

## 3. Minimum domain model

### Boundary and entities

Security → market snapshot → setup instance → personal watchlist item → trade plan → executions/position → review. Account và cash movements phục vụ equity/risk; event calendar gắn security hoặc toàn thị trường. TradingView là nơi xem chart chuyên sâu; broker là nguồn fill/account thật. Không đặt lệnh tự động trong scope đề xuất đầu tiên. Thuế và báo cáo pháp định chưa áp dụng: mục tiêu là analytics trước thuế, không phải tax engine.

### State / process

- Setup: detected → monitoring → triggered → invalidated/expired; rejected/dismissed là lựa chọn người dùng, không xóa lịch sử.
- Plan: draft → ready → active sau khi có fill → closed/cancelled; sửa plan lưu version và lý do.
- Order/fill: phân biệt pending, partial, filled, cancelled khi nhập; trigger không tự tạo vị thế.
- Alert: evaluated → queued → delivered/failed/expired; cùng setup/rule/session chỉ thông báo một lần trừ khi có chuyển trạng thái mới.

### Governing logic

- ATR% = ATR / close × 100; ATR method/period là config có version, đề xuất bắt đầu Wilder 14 nhưng chưa coi là tối ưu.
- Distance-to-trigger và distance-to-invalidation có cả USD, % và đơn vị ATR. Weekly indicators chỉ xác nhận trên tuần đã chốt; tuần đang chạy hiển thị provisional riêng.
- Size nguyên cổ phiếu: tìm q lớn nhất sao cho q × |entry − stop| + estimated_cost(q) ≤ risk_budget; đồng thời thỏa capital/buying-power, concentration và liquidity constraints. Không hardcode mức risk% mặc định cho người dùng.
- Long: stop < entry, target nếu có > entry; short đảo chiều bất đẳng thức. Stop bằng entry/thiếu, giá sai, equity không dương hoặc dữ liệu quá cũ → không trả size hợp lệ.
- Net R/R của một target: (q × favorable_distance − estimated_profit_path_cost) / (q × stop_distance + estimated_loss_path_cost). Không đặt target chỉ để đạt R/R mong muốn; phải ghi căn cứ cấu trúc hoặc exit rule. Hỗ trợ trailing/time exit không có target cố định.
- Initial R cố định tại lúc bắt đầu trade; R realized = net realized P&L / initial R. Add-on/partial exit phải có quy ước rõ và lưu lịch sử, không âm thầm đổi mẫu số để làm đẹp thống kê.
- P&L dùng actual fills và fees; slippage là chênh lệch với giá tham chiếu, không trừ thêm lần nữa vào P&L đã tính bằng fill thật. Borrow/financing và dividend obligations áp dụng riêng cho short nếu phát sinh.
- Risk-to-stop gộp theo giả định stop fill; hiển thị riêng stress gap loss. Không trình bày portfolio heat như worst-case loss.

### Inputs

| Input | Type / unit | Range/default | Source | Confidence/requirement |
|---|---|---|---|---|
| OHLCV | USD/share, shares, session | H/L/O/C hợp lệ; daily + weekly derived | Provider hiện tại | Bắt buộc cho setup; adjustment basis hiển thị rõ |
| Entry/stop/exit rule | USD/share hoặc rule | Không có default tùy tiện; user xác nhận | Setup + user | Bắt buộc để plan ready/size |
| Equity/cash/buying power | Currency amount + as_of | Equity >0; budget do user đặt | Nhập tay/CSV, broker sau | Bắt buộc để sizing |
| Risk constraints | USD, % equity, exposure caps | User policy, có version | User | Chưa được người dùng xác định |
| Position/fill | qty, side, price, fees, timestamp, id | qty>0; dedup by execution identity | Broker export/nhập tay | Bắt buộc để portfolio/journal thật |
| Earnings/events | timestamp, confidence, source | confirmed/estimated/unknown | Event provider | Unknown không đồng nghĩa không có sự kiện |
| Costs | USD/trade/share hoặc fee rule | Broker-specific; tách estimated/actual | User/broker | Short borrow không được giả định bằng 0 |
| Rules | setup/risk/config version | Explicit immutable revision | App/user | Bắt buộc cho reproducibility |

### Outputs

| Output | Meaning / unit | Acceptance |
|---|---|---|
| Today workspace | Các việc cần xem theo priority | Active positions/events trước ứng viên mới |
| Setup detail | Trend, trigger, extension, invalidation | Điều kiện và evidence tách rõ |
| Trade plan | Giá/rule, expiry, estimated size/cost/R | Không size khi thiếu inputs quan trọng |
| Portfolio view | USD/% gross/net exposure, heat, scenarios | Đối chiếu holdings/equity và test stress |
| Journal | Net USD, R, adherence, MAE/MFE | Reconcile broker, costs không double count |
| Scanner evaluation | Outcomes theo horizon/setup/regime | Nêu sample size, missing, uncertainty và baseline |

### Constraints and failures

EOD cảnh báo sau chốt phiên, không hứa realtime execution. Máy local tắt thì job không chạy: cần catch-up và trạng thái missed run. Raw tradable prices và adjusted analytical prices phải được phân biệt trước khi xuất entry/stop. Missing/stale positions phải làm portfolio view báo incomplete. Dữ liệu daily có thể không biết thứ tự chạm stop và target trong cùng nến; không chọn đường có lợi. Import phải idempotent, hỗ trợ sửa mapping và undo batch. Backup/restore cần kiểm chứng trước khi journal trở thành nguồn dữ liệu quan trọng.

## 4. Evidence and uncertainty ledger

| Claim/decision | Class | Evidence | Impact if wrong | Validation / owner |
|---|---|---|---|---|
| Muốn công cụ swing cổ phiếu chuyên nghiệp | User fact | Yêu cầu và clarification | Scope | Người dùng |
| Đã có compact table, search, FA/score persistence | Verified code fact | candidate_cards, database, repository | Đề xuất trùng lặp | Đã đọc; chưa UI-test |
| Chưa có plan/positions/journal/alerts | Verified inspected-code gap | Schema, repository, app/analytics inventory | Thiếu closed-loop workflow | Xác nhận qua module acceptance |
| Tiếp tục S&P500, EOD, manual execution | Assumption | Scope hiện tại | Thay data/architecture nếu đổi | Người dùng, trước nâng execution scope |
| Size/risk policy và broker chưa biết | Open assumption | Chưa có yêu cầu cụ thể | Không thể đưa thông số giao dịch thật | Người dùng trước triển khai sizing |
| Thêm module sẽ tăng profitability | Chưa có bằng chứng | Không có outcome research | Kỳ vọng sai | Không đưa ra claim này |
| Dùng CSV trước broker API | Proposal | Nhỏ và dễ đối chiếu | Có thao tác thủ công | Đánh giá workflow/import accuracy |

## 5. Feature map và đối chiếu

### Core — thứ tự triển khai đề xuất

| Module | Tính năng cụ thể | Quyết định hỗ trợ | Tiêu chí hoàn thành nhỏ nhất |
|---|---|---|---|
| 1. Personal watchlist + Today | Pin, notes, priority, dismiss, expiry; list need-review hôm nay | Hôm nay cần xử lý việc nào? | Reload và đổi snapshot vẫn giữ danh sách; có lý do thêm/bỏ |
| 2. Setup detail + playbook | Weekly/daily context; breakout/pullback/reversal tách subtype; ATR%, extension, trigger/invalidation, dollar volume; version checklist | Setup có phù hợp và còn điểm giao dịch không? | Mỗi candidate drill-down ra evidence số và tiêu chí chưa đạt |
| 3. Trade planner + sizing | Entry/stop/time exit/target tùy chọn; expiry; costs; size theo constraints | Nếu giao dịch thì kế hoạch cụ thể là gì? | Kế hoạch bất biến lúc entry; numerical/risk validation trước sử dụng thật |
| 4. Positions + portfolio guardrails | Nhập holdings; gross/net, sector/theme exposure; heat, concentration, gap scenarios; before/after candidate | Có nên thêm lệnh này vào danh mục? | Import khớp; dữ liệu thiếu bị nhận diện; không nhầm hedge là xóa risk |
| 5. Position management | Review queue cho invalidation/earnings/expiry/time stop; exit rule và sửa stop có lý do | Giữ, giảm, thoát hoặc cần xem lại? | Alerts không tự thay kế hoạch hoặc tự giả định có fill |
| 6. Journal + weekly review | Fill import; setup/regime tag; screenshot/notes; net P&L, R, MAE/MFE; plan adherence | Lỗ do setup hay do thực thi? | Số liệu khớp broker; partial fills/fees/splits được xử lý |
| 7. Scanner quality report | Outcomes mọi signal 5/10/20 phiên, baseline, setup/regime breakdown, stability | Bộ lọc và score có giúp ích không? | Theo thời gian, point-in-time, không dùng future info; báo uncertainty |

Watchlist → plan → position → review nên chia sẻ cùng setup_id và snapshot_id. Không xây bốn danh sách rời nhau rồi yêu cầu người dùng nhập lại dữ liệu.

### Trust — làm cùng các module trên

Market calendar đủ holidays/early closes; event confidence; data freshness theo metric; chart/data adjustment basis; history rule/config; backup và restore; run health; signal explanation và “why rejected”. Riêng session helper hiện chỉ xét weekday và 16:00 ET, chưa đủ lịch nghỉ/đóng sớm. [NYSE lịch giao dịch](https://www.nyse.com/markets/hours-calendars) xác nhận có ngày nghỉ và phiên đóng sớm. Đây là điểm nền tảng còn phải hoàn tất trước workflow vận hành thường xuyên.

### Explore

- Market regime dashboard có trend/breadth/volatility và persistence; dùng làm bối cảnh và phân nhóm nghiên cứu trước khi biến thành hard gate.
- Rank history 1W/1M, leader persistence, participation nội bộ nhóm; nhận diện rotation từ chuỗi thời gian thay vì snapshot đơn lẻ.
- Saved screens theo playbook; filter earnings distance, ATR%, dollar volume, extension, industry, status; dữ liệu cột giữ numeric để sort đúng.
- Rule-based alerts cho watchlist, invalidation, earnings, data failure; dedup/cooldown/expiry/delivery log. Không gửi “mã vẫn thỏa điều kiện” lặp lại mỗi lần refresh.
- Chart preview gọn gồm daily/weekly, volume, RS line, trigger/stop; chart chuyên sâu tiếp tục qua TradingView.
- Earnings context thêm lịch sử surprise và price reaction chỉ khi nguồn đủ rõ; ưu tiên event timing trước việc thêm nhiều chỉ số FA.

### Later

Mở universe ngoài S&P500 (có thể giúp tìm growth leaders nhưng tăng nhu cầu dữ liệu/coverage); VCP/base patterns sau khi playbook causal được xác định; broker read-only integration sau CSV; intraday confirmations sau khi cadence/data contract đổi. Auto execution, options flow, ML stock-picking và terminal đa tài sản chưa vào scope. Dùng công cụ ngoài có thể đáp ứng một module; không bắt buộc tự xây toàn bộ.

### Đối chiếu nguồn chính thức

| Nền tảng | Năng lực đã xác minh | Bài học phù hợp cho Market Radar |
|---|---|---|
| [TC2000](https://www.tc2000.com/features/overview) | Charting/screening, favorites watchlist và notepad | Tổ chức phiên phân tích, lưu danh sách và ghi chú |
| [TrendSpider alerts](https://trendspider.com/product/trade-timing-and-execution-tools/) | Multi-factor/multi-timeframe alerts | Quy tắc cảnh báo bám playbook và trạng thái |
| [TrendSpider Strategy Tester](https://help.trendspider.com/kb/strategy-tester/accessing-and-using-the-strategy-tester) | Định nghĩa entry/exit rồi test lịch sử | Rule có thể kiểm chứng; không chỉ nhãn setup. Trang này ghi tester chọn một timeframe — không suy từ MTFA sang backtest đa timeframe |
| [IBKR Risk Navigator](https://www.interactivebrokers.com/campus/trading-lessons/build-a-portfolio-using-tws-risk-navigator/) | Danh mục giả định what-if | Xem tác động lệnh mới trên danh mục hiện có |
| [TradesViz](https://www.tradesviz.com/about/) | Executions, targets, MFE/MAE, notes, plan adherence, slippage/commissions analysis | Nhật ký nối kế hoạch với kết quả và review |

Đây là đối chiếu chức năng, không khẳng định các tính năng miễn phí, dễ sao chép hoặc tạo lợi nhuận. Không cần mua/cài các nền tảng này để thực hiện review.

## 6. Acceptance and validation

1. Một phiên mẫu: mở Today → xem vị thế cần chú ý → đánh giá shortlist → lưu plan hoặc reject có lý do → import fills → weekly review. Không phải nhập lại symbol/setup/giá tham chiếu ở từng bước.
2. Planner: tests long/short, stop sai phía/bằng entry, missing costs, q=0, gap vượt entry zone, thiếu equity và constraint xung đột. Tính độc lập bằng worksheet/reference cases trước dùng thật; reviewer có kinh nghiệm risk xác nhận conventions.
3. Portfolio: duplicate CSV không nhân đôi vị thế; long/short/partial fills, phí, cash movements và corporate actions đối chiếu broker. Tổng USD/% phải có currency/as_of và pricing policy rõ.
4. Journal: net P&L khớp broker trong tolerance theo rounding của báo cáo; ban đầu đề xuất 0.01 USD với fixture USD, sai khác phải giải thích, không tự sửa dữ liệu cho khớp. Initial R và plan revisions không thay đổi lịch sử âm thầm.
5. Alerts: một event một notification, retry không gửi trùng; lỗi delivery có log; hết hạn ngừng theo dõi; downtime có catch-up rõ. EOD không được báo đạt trigger trước khi bar đóng theo calendar.
6. Outcomes: chọn signal time, horizon, entry convention và benchmark trước khi đo; không coi mọi ngày cùng một setup là các trade độc lập. Có temporal holdout, sample size và uncertainty. Forward-return report chưa đủ để tuyên bố P&L chiến lược; execution backtest phải bổ sung fees/slippage/borrow và ambiguous-bar policy.
7. Weekly bars: các fixture tuần nghỉ lễ/tuần đang chạy; không dùng weekly close tương lai cho tín hiệu giữa tuần.
8. Vận hành: restore backup vào DB mới, đối chiếu số plan/fill/journal và audit ids; không chỉ kiểm tra file backup tồn tại.

## 7. Open decisions

Không cần thêm câu hỏi để hoàn thành review. Mặc định đề xuất: cổ phiếu S&P500, EOD, thủ công, dùng TradingView. Trước module giao dịch thật cần chốt: (1) broker/account currency/import format; (2) playbook và thời gian giữ dự kiến; (3) ngân sách rủi ro và giới hạn tập trung do người dùng đặt. Không tự chọn risk% hay stop multiple như khuyến nghị cá nhân.

## 8. Readiness score

Chấm hiện trạng đối với scope workstation đầy đủ, không chấm lại riêng screener.

| Dimension | Score | Gap |
|---|---|---|
| Outcome/audience/fidelity | 2 | Outcome đã xác định; phạm vi module đề xuất rõ |
| Boundary/entities/state | 1 | Đã có snapshot; thiếu plan/position lifecycle |
| Governing logic | 1 | Screening có; execution/risk conventions chưa chốt |
| Inputs/outputs/units | 1 | Chưa có account/fill/cost data contracts thực tế |
| Constraints/failures | 1 | Cần calendar đầy đủ và portfolio/import failure policy |
| Evidence/assumptions | 2 | Code và nguồn chính thức; đề xuất tách khỏi facts |
| Validation/tolerances | 1 | Có phương án review, chưa nghiệm thu module mới |
| MVP/deferred scope | 2 | Đã chia thứ tự và scope ngoài |

11/16. READY WITH ASSUMPTIONS cho refinement phạm vi; NOT READY để giao dùng thật phần sizing/risk chưa triển khai/kiểm chứng. Không chấm score như một giấy chứng nhận chuyên môn.

## 9. Kế hoạch làm rõ và kiểm chứng trước build handoff cho toàn hệ thống

- Đợt A: Today + personal watchlist + setup detail/playbook, đồng thời hoàn tất calendar/provenance. Thành công khi người dùng chuẩn bị được shortlist và lý do chọn/bỏ mỗi phiên.
- Đợt B: Trade planner + holdings import + portfolio guardrails. Chốt broker/risk conventions, chạy reference cases và người có kinh nghiệm kiểm tra trước dùng sizing thật.
- Đợt C: Position review + journal/fill import + weekly review. Thành công khi đối chiếu được toàn bộ giao dịch và costs với broker, giải thích sai lệch execution với plan.
- Đợt D: Signal outcomes + alerts + cải tiến score có kiểm chứng. Không tối ưu score bằng kết quả trên chính tập đã chọn rule.

Ba ưu tiên có giá trị trực tiếp nhất sau bản hiện tại: **personal watchlist và setup detail; trade plan có risk sizing; positions/journal nối liền kế hoạch**. Mở rộng indicator/universe chỉ sau khi có nhu cầu cụ thể hoặc bằng chứng thiếu cơ hội.
