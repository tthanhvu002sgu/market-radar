# Market Radar

> Dashboard chạy trên máy cá nhân giúp đi từ bức tranh vĩ mô/độ rộng S&P 500 đến danh sách cổ phiếu đáng xem cho swing trading trên TradingView với chi phí dữ liệu 0 đồng.

---

## 0. Setup (khuyến nghị)

### Yêu cầu môi trường
- Python 3.10 trở lên (khuyến nghị Python 3.12+)
- Mạng Internet để tải dữ liệu mở (Wikipedia & Yahoo Finance)

### Cài đặt & Khởi chạy

```bash
# 1. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 2. Cập nhật dữ liệu thị trường và nạp snapshot lần đầu
python -m jobs.update_pipeline

# (Tùy chọn) Chạy cập nhật tự động định kỳ (ví dụ mỗi 6 tiếng):
# Cách A - Chạy ngầm bằng Windows Task Scheduler (xem jobs/run_update.bat)
# Cách B - Chạy Python scheduler: python -m jobs.scheduler --interval 6

# 3. Khởi chạy Dashboard Streamlit
streamlit run app/main.py

# 4. Chạy kiểm thử tự động
pytest tests/ -v
```

### Tài liệu hướng dẫn sử dụng
- [📘 Hướng dẫn chi tiết từng tính năng (Feature Manual)](docs/HUONG_DAN_CHI_TIET_TINH_NANG.md): Tra cứu toàn diện giao diện, công thức kỹ thuật, các ngưỡng định lượng, 3 trụ cột điều hướng, bảng tham chiếu và nguyên tắc dữ liệu 0 đồng.
- [📗 Cẩm nang theo kịch bản sử dụng (Scenario Playbook)](docs/KICH_BAN_SU_DUNG.md): Hướng dẫn thực chiến 8 kịch bản (15 phút trước giờ mở cửa, săn Breakout, bắt đáy Mean Reversion, bán khống Downtrend, quản lý rủi ro mùa BCTC, rà soát cuối tuần, kiểm toán Alpha tín hiệu và vận hành dữ liệu).

### Biến môi trường
Xem file `.env.example`:
| Tên biến | Bắt buộc | Mặc định | Mô tả |
|---|---|---|---|
| `DB_PATH` | Không | `data/market_radar.db` | Đường dẫn file cơ sở dữ liệu SQLite |
| `HISTORICAL_DAYS` | Không | `365` | Số ngày lịch sử nến ngày tải về |
| `MIN_COVERAGE_PCT` | Không | `0.95` | Ngưỡng cảnh báo độ bao phủ universe |
| `LOG_LEVEL` | Không | `INFO` | Mức log hệ thống |

---

## 1. Tổng quan tính năng

| ID | Tính năng | Mô tả ngắn | Trạng thái |
|---|---|---|---|
| M01 | Tổng quan thị trường & Độ rộng tham gia | Hiệu suất SPY/RSP; chuỗi thời gian độ rộng (A/D Line, AD Volume Line & %, MA20/50/200 breadth history với mẫu số quan sát hợp lệ); tỷ suất Equal-Weight vs Median; Net Breadth | done |
| M02 | Luân chuyển ngành & Sức khỏe nội bộ | Tách bạch luân chuyển (Rotation 4 góc phần tư có vệt lịch sử 10 phiên, X=100*(R/EMA20(R)-1), Y=X-X_t-5) khỏi sức khỏe nội bộ (phát hiện phân kỳ mega-cap, tỷ trọng GTGD ước tính turnover_est, Top 5 concentration) | done |
| M03 | Nhóm ngành nhỏ | Drill-down xem chi tiết các Sub-Industry trong từng ngành, số mã thành phần, lợi suất trung bình và mã dẫn đầu | done |
| M04 | 4 nhóm ứng viên giao dịch | Sàng lọc 4 nhóm ứng viên swing trade: Long Tiếp Diễn, Short Tiếp Diễn, Long Đảo Chiều, Short Đảo Chiều; có Watchlist cho tín hiệu mâu thuẫn; không ép hạn ngạch | done |
| M05 | Chi tiết cổ phiếu & TradingView | Thẻ giải trình chi tiết lý do kỹ thuật (MA, RS, Volume), bối cảnh FA doanh nghiệp, lịch Earnings, nút 1-click mở TradingView | done |
| M06 | Thay đổi và lịch sử | Lưu trữ snapshot SQLite mỗi chu kỳ; so sánh biến động giữa các snapshot: mã mới lọt/rời danh sách, biến động thứ hạng ngành; hỗ trợ xuất CSV | done |
| M07 | Chất lượng dữ liệu & 0đ | Nguồn mở 100% (Wikipedia + Yahoo Finance), giám sát thời điểm `as_of`, tỷ lệ bao phủ (>95%), danh sách mã lỗi, cơ chế ProcessLock chống chạy trùng | done |
| M08 | Ma trận Nhóm ngành O'Neil | Xếp hạng đa khung thời gian 127 GICS Sub-Industries theo William O'Neil; chuẩn hóa Percentile 1-99, điểm COMP và BLEND; heatmap với chế độ xem kép (COMP/BLEND vs Breadth/Median); stock pills link TradingView | done |
| M09 | Chi tiết Setup & Mức kỹ thuật | Trang chi tiết từng setup: Bối cảnh đa khung (Ngày/Tuần, tuần chưa đóng gắn nhãn riêng), mức kích hoạt (Trigger), vô hiệu (Invalidation), hỗ trợ/kháng cự kèm căn cứ; biến động ATR14, ATR%, khoảng cách MA; thanh khoản (SMA20 vol, dollar volume, RV); checklist điều kiện đạt/chưa đạt/thiếu dữ liệu; biểu đồ gọn point-in-time và xuất CSV cho Excel | done |
| M10 | Trang “Hôm nay” & Cảnh báo | Bốn nhóm sự kiện hàng đầu: cơ hội mới, thay đổi setup, sự kiện BCTC sắp tới (<=14 ngày), biến động thị trường/ngành; chống trùng lặp, so sánh giữa các phiên giao dịch; lọc và đánh dấu đã đọc | done |
| M11 | Đo chất lượng bộ lọc (Outcomes) | Đánh giá độc lập chất lượng scanner: ghi nhận giá Open phiên kế tiếp, theo dõi setup theo đợt (streak), forward outcomes 5/10/20 phiên, chênh lệch vs SPY, MFE/MAE (% và ATR), kiểm định tính đơn điệu của score (Top vs Bottom quartile) | done |
| M12 | Lịch giao dịch NYSE/NASDAQ chuẩn | Bộ lịch thị trường Mỹ đầy đủ ngày nghỉ lễ, phiên đóng sớm (13:00 ET), xác định chính xác phiên giao dịch EOD và trạng thái kết thúc tuần | done |
| M13 | Nhận diện Nến Nhật & Bối cảnh FA | Nhận diện nến ngày gần nhất (Doji, Marubozu, Hammer, Shooting Star, Engulfing, Inside/Outside); thông dịch 3 dòng theo ngữ cảnh setup; khảo sát lợi thế mẫu nến (Candlestick Edge Audit); phục hồi bối cảnh FA tự động từ database | done |
| M14 | Bối cảnh FA & Xuất xứ dữ liệu (D-01, R-02) | Bổ sung kỳ tài chính (Fiscal Period MRQ/FY), ngày kết thúc kỳ (`period_end`), thời điểm thu thập (`retrieved_at`), loại kỳ (Quarterly YoY), đồng tiền (USD), nguồn cấp (Yahoo Finance Số liệu tổng hợp / Aggregate), nút 1-click tra cứu hồ sơ SEC EDGAR; kiểm soát BCTC cũ quá 180 ngày | done |
| M15 | Dòng sự kiện doanh nghiệp & Phân tách Xuất xứ (D-02, R-01) | Phân tách rành mạch sự kiện scanner EOD (`analytic_event`, link TradingView) khỏi sự kiện doanh nghiệp bên ngoài (`external_company_event`, Yahoo Finance Calendar ước tính kèm cảnh báo chưa kiểm chứng, nút tra cứu EDGAR); ghi nhận `published_at` và `received_at` | chưa triển khai SEC ingestion (đã phân tách xuất xứ & cảnh báo) |
| M16 | Hồ sơ Áp lực Mua/Bán Đa phiên & Bỏ từ vựng gây hiểu lầm (D-03, R-05) | Thay thế các cụm từ gán ý chí chủ quan ("dòng tiền gom hàng/phe bán áp đảo") bằng sự thật quan sát giá-volume ("bằng chứng thuận/mâu thuẫn"); hồ sơ áp lực 1/3/5 phiên trích xuất 3 khối bằng chứng cấu trúc | done |
| M17 | Đo lường Outcomes Swing Trong Tuần & Chốt Cuối Tuần (D-04) | Đo lường hiệu quả bộ lọc theo chu kỳ giữ vài ngày không ôm qua tuần (1, 2, 3, 4 phiên và Chốt cuối tuần 99); tự động gắn cờ bỏ qua ca vào cuối tuần (`no_window_in_week`); phân nhóm theo Thứ và Chiều Long/Short; cảnh báo Gross Return vs P&L thực | done |
| M18 | Đồng hồ Thị trường, Độ tươi & Minh bạch Phạm vi S&P 500 (D-05/06) | Đồng hồ kép New York (ET) & Việt Nam (ICT), trạng thái phiên NYSE thời gian thực; tính toán độ trễ phiên (`compute_session_age`); công bố rõ ràng phạm vi vũ trụ 503 mã Large Cap S&P 500 và bản chất EOD snapshot | done |
| M19 | Biểu đồ 3 Chỉ số Lớn (S&P 500, NASDAQ, DOW) | 3 thẻ biểu đồ nến trực quan cho S&P 500, NASDAQ, DOW kèm vạch tham chiếu đóng phiên trước, huy hiệu giá vàng, cột Relative Volume, hỗ trợ chuyển đổi nến 5m trong ngày và nến ngày 30 phiên | done |
| M20 | Thanh Bar Đối Chiếu Tỷ Lệ Độ Rộng Thị Trường | Nâng cấp các thẻ đo lường độ rộng (Advancing/Declining, New High/Low, SMA50, SMA200, Xung lực Bull/Bear) thành thanh bar đối chiếu hai màu xanh/đỏ trực quan thay vì chỉ có số | done |
| M21 | Phân Hệ Lịch Báo Cáo Tài Chính (Earnings Calendar) | Trạm làm việc theo dõi lịch BCTC toàn diện: bộ lọc tuần này/tuần tới/14 ngày, phân loại BMO/AMC, bộ lọc S&P 500 & Ứng viên Radar, chế độ Lịch tuần và Bảng chi tiết kèm link TradingView & SEC EDGAR | done |
| M22 | Nhận diện Nền giá (Base Building & Đang xây nền) | Phát hiện cấu trúc tích lũy đi ngang (cửa sổ 20 phiên, yêu cầu >=40 nến): biên độ <=12%, ER <=0.35, độ lệch tâm <=0.30, thu hẹp TR/Vol <=0.80 cho trạng thái tight; đóng băng biên độ từ phiên phát hiện; đánh giá breakout/breakdown nhân quả tại T theo biên T-1; cân bằng volume có dấu (signed volume balance); bối cảnh MA50/200, RS vs SPY, áp lực P/V; theo dõi vòng đời nền (forming, tight, breakout, breakdown, invalidated, closed); cô lập storage với Signal Outcomes | done |

### Chi tiết các luồng chính
- **M01 — Thị trường & Độ rộng Tham gia:** Tóm tắt tự động bằng câu văn có số liệu thực tế; phát hiện nhanh đà tăng do nhóm vốn hóa lớn kéo hay lan tỏa toàn thị trường (so sánh SPY vs RSP); phân tích chuỗi thời gian A/D Line, AD Volume Line (khối lượng mã tăng vs mã giảm), lịch sử % trên MA20/50/200 (loại trừ mã thiếu MA khỏi mẫu số), Net Breadth và so sánh lợi suất Equal-Weight vs Median.
- **M02 & M03 — Luân chuyển & Sức khỏe Ngành:** Biểu đồ luân chuyển 4 góc phần tư (Leading, Weakening, Lagging, Improving) với vệt lịch sử 10 phiên theo mốc point-in-time `as_of`; tách bạch luân chuyển tương đối khỏi sức khỏe nội bộ ngành; nhận diện phân kỳ méo mó vốn hóa lớn (mega-cap masking); giám sát thanh khoản ước tính (`turnover_est`) và mức độ tập trung Top 5 mã.
- **M04 & M05 — Ứng viên:** 4 tab chuyên biệt cho 4 chiến thuật swing. Mỗi mã có thẻ bằng chứng kỹ thuật và gắn cờ cơ bản. Với các mã Short luôn có nhãn cảnh báo *"Chưa xác minh khả năng short / phí vay"*.
- **M06 — Lịch sử:** Cho phép chọn xem lại các snapshot cũ trong sidebar và hiển thị bảng so sánh delta trực quan.
- **M08 — O'Neil Heatmap & Leaders:** Ma trận nhiệt trực quan hóa sức mạnh 127 nhóm ngành; trích xuất các cổ phiếu dẫn đầu dạng pill màu xanh/đỏ click mở ngay TradingView; gắn cờ ⭐ O'Neil Leader cho ứng viên swing thuộc Top 20% ngành mạnh nhất.
- **M09 — Chi tiết Setup & Playbook:** Cung cấp thông tin mức giá tham chiếu phân tích, căn cứ xác định, checklist đạt/chưa đạt và biểu đồ gọn point-in-time (không rò rỉ dữ liệu tương lai) để người dùng ghi chép đưa sang Excel cá nhân.
- **M10 — Trang Hôm nay:** Bàn làm việc đầu ngày hiển thị rõ *điều gì thay đổi -> bằng chứng -> mở chi tiết -> TradingView*, tạo sau mỗi lần cập nhật EOD thành công với cơ chế chống trùng lặp tuyệt đối.
- **M11, M17 — Đo chất lượng bộ lọc:** Thống kê khách quan xác suất thắng, alpha so với SPY, MFE/MAE và kiểm toán score để biết bộ lọc có thực sự mang lại lợi thế thống kê hay không; mở rộng đo lường kỳ hạn giữ ngắn trong tuần (1-4 phiên, week-close) và phân nhóm theo Thứ vào lệnh cùng Chiều Long/Short.
- **M13, M14 — Nhận diện Nến Nhật & Bối cảnh FA:** Tách bạch hình học nến khỏi vị trí xuất hiện (VD: Hammer tại hỗ trợ MA20 xác nhận phản ứng vs rủi ro mua đuổi khi tăng xa >1.5 ATR); công bố đầy đủ ngưỡng nhận diện; tích hợp Candlestick Edge Audit trong đo lường tín hiệu; khôi phục hiển thị chỉ số FA (tăng trưởng Doanh thu, EPS, Margin, kỳ BCTC) kèm xuất xứ nguồn và nút mở trực tiếp SEC EDGAR.
- **M15, M16, M18 — Minh bạch Miền & Giám sát Thị trường:** Đồng hồ thị trường New York/Việt Nam và trạng thái NYSE; giám sát độ tươi snapshot (`as_of`) và cảnh báo dữ liệu lịch sử; hồ sơ áp lực giá-volume 1/3/5 phiên không giả định order book; tuyên bố rõ ràng phạm vi vũ trụ 503 mã thành phần S&P 500.
- **M22 — Nhận diện Nền Giá (Đang Xây Nền):** Module chuyên biệt trong tab Ứng viên giúp theo dõi cổ phiếu tích lũy trước breakout. Tách bạch cấu trúc hình học nền giá khỏi bằng chứng tích lũy volume; hiển thị rõ ràng ngày phát hiện ban đầu (`detected_at`) và cửa sổ 20 phiên hiện tại (`window_start` -> `window_end`); checklist điều kiện đạt/chưa đạt; xuất CSV; và sinh sự kiện cảnh báo EOD chống trùng lặp.


---

## 2. Kiến trúc hệ thống

### Stack công nghệ
| Layer | Công nghệ | Vai trò |
|---|---|---|
| **Frontend UI** | Streamlit + Plotly | Dashboard giao diện web local, bảng tương tác, biểu đồ gauge và heatmap ngành |
| **Backend & Analytics** | Python 3.12, pandas, numpy | Xử lý dữ liệu định lượng, tính MA, Relative Strength, Breadth và luật lọc ứng viên |
| **Lưu trữ (Data)** | SQLite (`sqlite3`) | Lưu trữ universe, nến ngày, chỉ số FA, và toàn bộ lịch sử snapshot phân tích |
| **Data Adapters** | Wikipedia Provider + YFinance Provider | Thu thập dữ liệu mở, chuẩn hóa mã (`BRK.B` -> `BRK-B`), tải song song với `ThreadPoolExecutor` |
| **Concurrency & Lock** | `ProcessLock` (file-based) | Đảm bảo an toàn tiến trình, chống chạy trùng lặp tác vụ cập nhật |

### Sơ đồ luồng dữ liệu
```text
[Wikipedia S&P 500] ──> [providers/sp500_provider] ──> [constituents table]
                                                              │
[Yahoo Finance API] ──> [providers/yfinance_provider] ─> [daily_bars table]
                                                              │
[SQLite Local DB]   <── [jobs/update_pipeline] <──────────────┤
        │                                                     ▼
        ├──> [analytics/market_calendar]     ──> [NYSE Holidays, Early Closes & Week Status]
        ├──> [analytics/market_breadth]      ──> [Market Breadth, ATR14, Weekly Context, RVOL]
        ├──> [analytics/market_participation]──> [Net Breadth, A/D & AD Vol Lines, Sector Health]
        ├──> [analytics/sector_rotation]     ──> [4 Quadrants Relative & Trend Rotation Trails]
        ├──> [analytics/sector_ranker]       ──> [11 GICS Sectors Ranking & Liquidity Top 5]
        ├──> [analytics/industry_ranker]     ──> [127 Sub-Industries O'Neil Heatmap]
        ├──> [analytics/setup_analyzer]      ──> [Technical Levels, Playbook, Checklist]
        ├──> [analytics/screening_rules]     ──> [4 Candidate Groups + Subtypes]
        ├──> [analytics/base_detector]       ──> [20-Bar Base Building, Frozen Bounds, Contraction, Evidence]
        ├──> [analytics/signal_events]       ──> [Deduplicated Cross-Session Events]
        ├──> [analytics/signal_outcomes]     ──> [Streaks, Forward Returns 5/10/20D, MFE/MAE]
        └──> [analytics/company_fa]          ──> [FA Flags & Earnings Status]
                     │
                     ▼
               [app/main.py (Streamlit - Kiến trúc 3 Trụ Cột / 2 Cấp điều hướng)]
                       ├──> [Pillar 1: 🎯 Hôm Nay & Ứng Viên]
                       │       ├──> [01 Hôm Nay (Today Dashboard & Events)]
                       │       ├──> [02 Ứng Viên & Setup Detail (TradingView + In-tab CSV Export)]
                       │       ├──> [03 Đang Xây Nền 🧱 (Base Watchlist, Checklist, Shaded Region Chart)]
                       │       └──> [04 Lịch Báo Cáo Tài Chính (Earnings Calendar)]
                       ├──> [Pillar 2: 🌐 Bản Đồ Thị Trường & Ngành]
                       │       ├──> [01 Bức Tranh Thị Trường (3 Major Indices + Contrast Bars + SPY vs RSP)]
                       │       ├──> [02 11 Ngành GICS (Sector Rotation & Drill-down)]
                       │       └──> [03 Ma Trận 127 Nhóm Ngành O'Neil (CANSLIM Percentile Matrix)]
                       └──> [Pillar 3: 📊 Đo Lường & Kiểm Toán]
                               ├──> [01 Hiệu Quả Tín Hiệu (Alpha Audit & Forward Outcomes)]
                               ├──> [02 So Sánh Snapshot (Delta History)]
                               └──> [03 Kiểm Toán Dữ Liệu & Vận Hành (0đ, Coverage, Quality)]
```

### Cấu trúc thư mục
```text
market radar/
├── app/                          # Giao diện ứng dụng Streamlit
│   ├── main.py                   # Entry point Dashboard 3 Trụ cột (Two-tier Navigation)
│   └── components/               # Các UI components tái sử dụng
│       ├── index_charts.py       # Cụm biểu đồ 3 chỉ số lớn S&P 500, NASDAQ, DOW (Intraday/Daily)
│       ├── earnings_calendar.py  # Phân hệ Lịch Báo cáo Tài chính (Earnings Calendar đa chế độ)
│       ├── today_dashboard.py    # Trang Hôm nay: 4 nhóm sự kiện, unread badge, action bar
│       ├── setup_detail.py       # Chi tiết setup: 3 tab nội bộ (Kỹ thuật/Chart, Nến/FA, Checklist/CSV)
│       ├── signal_performance.py # Đo chất lượng bộ lọc: 5/10/20d returns, SPY alpha, MFE/MAE
│       ├── candidate_cards.py    # Thẻ ứng viên 4 nhóm, cờ O'Neil, xuất CSV tại chỗ, bảng số liệu
│       ├── metrics_cards.py      # Bức tranh thị trường, thanh bar đối chiếu tỉ lệ, A/D Lines, SPY vs RSP
│       ├── sector_table.py       # Luân chuyển 4 góc phần tư (trail), sức khỏe ngành, drill-down
│       ├── industry_heatmap.py   # Ma trận Heatmap 127 nhóm ngành & stock pills CANSLIM (dual-mode)
│       └── base_watchlist.py     # Danh sách & biểu đồ Đang Xây Nền, vùng nền tô bóng, checklist định lượng
├── providers/                    # Adapter kết nối và thu thập dữ liệu
│   ├── base.py                   # Interface trừu tượng BaseUniverse & BaseMarketData
│   ├── sp500_provider.py         # Lấy danh sách S&P 500 & phân ngành từ Wikipedia
│   └── yfinance_provider.py      # Tải batch nến ngày, ETF và FA/Earnings song song
├── storage/                      # Cơ sở dữ liệu và lưu trữ
│   ├── database.py               # Kết nối SQLite & Safe Migrations (history, rotation, health, base_snapshots)
│   ├── repository.py             # CRUD: universe, bars, snapshots, events, signal outcomes, base_snapshots
│   └── lock.py                   # Khóa tiến trình chống chạy đồng thời (ProcessLock)
├── analytics/                    # Động cơ phân tích định lượng & sàng lọc
│   ├── market_calendar.py        # Lịch nghỉ lễ NYSE, phiên đóng sớm, kiểm soát phiên EOD
│   ├── market_participation.py   # Chuỗi thời gian độ rộng thị trường, A/D line, sector health
│   ├── sector_rotation.py        # Luân chuyển 4 góc phần tư X/Y, vệt 10 phiên, bối cảnh xu hướng
│   ├── setup_analyzer.py         # Mức kỹ thuật (trigger/inv/sup/res), ATR, checklist
│   ├── base_detector.py          # Phát hiện nền giá 20 phiên, co hẹp TR/Vol, ER, Center Shift, OBV bias, đóng băng biên
│   ├── signal_events.py          # Phát hiện biến động liên phiên chống trùng lặp
│   ├── signal_outcomes.py        # Theo dõi đợt tín hiệu, forward return 5/10/20D, MFE/MAE
│   ├── market_breadth.py         # Tính MA20/50/200, ATR14, RVOL 20 phiên, Weekly context
│   ├── sector_ranker.py          # Relative strength 1W/1M/3M 11 Sector, thanh khoản, Top 5
│   ├── industry_ranker.py        # Xếp hạng đa khung thời gian 127 nhóm ngành, COMP, BLEND
│   ├── screening_rules.py        # Sàng lọc ứng viên, phân loại subtype, gắn nhãn O'Neil
│   └── company_fa.py             # Đánh giá FA, cảnh báo đòn bẩy, ngoại lệ ngân hàng
├── jobs/                         # Tác vụ cập nhật dữ liệu tự động
│   ├── update_pipeline.py        # Pipeline cập nhật toàn diện và tạo snapshot (v2.1)
│   ├── scheduler.py              # Bộ lập lịch chạy ngầm định kỳ (mặc định mỗi 6 tiếng)
│   ├── run_update.bat            # Batch script tích hợp Windows Task Scheduler & ghi log
│   └── update_signal_outcomes.py # Job cập nhật kết quả forward outcomes cho mọi tín hiệu
├── config/                       # Tham số cấu hình
│   ├── settings.py               # Ngưỡng kỹ thuật, tham số trọng số O'Neil COMP/BLEND
│   └── sector_mappings.py        # Bản đồ 11 GICS Sectors <-> 11 SPDR Sector ETFs
├── data/                         # Thư mục chứa cơ sở dữ liệu SQLite local
│   ├── market_radar.db           # SQLite database
│   └── market_radar.db.bak       # Backup database an toàn
├── tests/                        # Bộ kiểm thử tự động (126 tests pass 100%)
│   ├── test_providers.py         # Kiểm tra adapter và chuẩn hóa ký hiệu
│   ├── test_analytics.py         # Kiểm tra kỹ thuật, O'Neil ranker, quy tắc ứng viên
│   ├── test_base_detector.py     # Kiểm tra nhận diện nền giá, co hẹp, biên đóng băng, chống lookahead
│   ├── test_storage.py           # Kiểm tra database SQLite, snapshot diff & migration
│   ├── test_storage_analytics_upgrade.py # Kiểm tra nâng cấp schema và tương thích snapshot
│   ├── test_market_participation.py      # Kiểm tra độ rộng thị trường, A/D Lines, sector health
│   ├── test_sector_rotation.py   # Kiểm tra luân chuyển 4 góc phần tư, vệt lịch sử point-in-time
│   ├── test_sector_table.py      # Kiểm tra an toàn giao diện bảng ngành và ma trận phụ trợ
│   ├── test_pipeline_e2e.py      # Kiểm tra tích hợp toàn diện trên database thực tế
│   ├── test_swing_features.py    # Kiểm tra calendar, setup analyzer, events, forward outcomes
│   └── test_domain_recheck.py    # Kiểm tra chấp nhận 6 lỗ hổng miền tài chính & migration (R-01 -> R-05)
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 3. Các component

| Component / Module | Path | Vai trò | Phụ thuộc chính |
|---|---|---|---|
| **App Entry Point** | `app/main.py` | Giao diện chính Streamlit kiến trúc 3 Trụ cột, điều hướng 2 cấp, quản lý snapshot | `streamlit`, `storage/repository` |
| **Major Indices UI** | `app/components/index_charts.py` | Cụm 3 thẻ biểu đồ nến S&P 500, NASDAQ, DOW kèm vạch tham chiếu, huy hiệu giá vàng, Relative Volume | `plotly`, `yfinance`, `streamlit` |
| **Earnings Calendar UI**| `app/components/earnings_calendar.py` | Trạm làm việc Lịch BCTC: Lịch tuần (BMO/AMC), bảng tương tác, bộ lọc S&P 500 và Ứng viên Radar | `streamlit`, `pandas`, `yfinance_provider` |
| **Today Dashboard UI**| `app/components/today_dashboard.py` | Bàn làm việc Hôm nay: 4 nhóm sự kiện, unread badge, action bar ổn định chiều cao | `streamlit`, `setup_detail` |
| **Setup Detail UI** | `app/components/setup_detail.py` | Modal chi tiết setup 3 tab nội bộ (Kỹ thuật/Chart PIT, Nến Nhật/FA, Checklist/Xuất CSV), loại bỏ cuộn dài | `plotly`, `streamlit`, `repository` |
| **Base Watchlist UI** | `app/components/base_watchlist.py` | Màn hình Đang Xây Nền: Thẻ dữ liệu 6 chỉ số định lượng, 4 bộ lọc vòng đời (Forming, Fresh breakouts, Climbing, Played out), loại bỏ biểu đồ nến, chia sẻ khối chỉ số sang Candidate Cards | `streamlit`, `repository` |
| **Signal Quality UI** | `app/components/signal_performance.py` | Màn hình đo chất lượng bộ lọc scanner: 5/10/20d returns, SPY alpha, MFE/MAE, Candlestick Edge Audit | `streamlit`, `signal_outcomes` |
| **Candidate Cards UI** | `app/components/candidate_cards.py` | Thẻ ứng viên 4 nhóm, cờ O'Neil Leader, nút xuất CSV tại chỗ, bảng số liệu định dạng chuẩn | `streamlit`, `setup_detail` |
| **Market Metrics UI** | `app/components/metrics_cards.py` | Thẻ thanh bar đối chiếu tỉ lệ xanh/đỏ (A/D, H/L, SMA50, SMA200, Bull/Bear), phân kỳ SPY vs RSP, time-series | `plotly`, `streamlit`, `index_charts` |
| **Sector Table UI** | `app/components/sector_table.py` | Bảng xếp hạng 11 ngành GICS, biểu đồ thanh RS, drill-down nhóm ngành con | `plotly`, `streamlit`, `pandas` |
| **Industry Heatmap UI**| `app/components/industry_heatmap.py` | Bảng nhiệt ma trận xếp hạng 127 nhóm ngành, điểm 1-99, stock pills link TV | `streamlit`, `pandas` |
| **Base Detector** | `analytics/base_detector.py` | Động cơ nhận diện nền 20 phiên: độ rộng <=12%, ER <=0.35, center shift <=0.30, co hẹp TR/Vol, OBV bias, đóng băng biên | `numpy`, `pandas` |
| **Market Calendar** | `analytics/market_calendar.py` | Tra cứu ngày nghỉ lễ NYSE/NASDAQ, phiên đóng sớm 13:00 ET, kiểm soát phiên | `datetime`, `zoneinfo` |
| **Setup Analyzer** | `analytics/setup_analyzer.py` | Trích xuất bằng chứng có cấu trúc: trigger, invalidation, support/res, nhận diện nến nhật (`analyze_candlestick`), thông dịch setup (`interpret_candlestick_in_setup`), checklist | `numpy`, `pandas` |
| **Signal Events** | `analytics/signal_events.py` | Phát hiện biến động liên phiên chống trùng lặp, cảnh báo EOD | `json`, `datetime` |
| **Signal Outcomes** | `analytics/signal_outcomes.py` | Đánh giá forward outcomes 5/10/20D, alpha vs SPY, MFE/MAE, kiểm toán score, phân rã kết quả theo mẫu nến | `numpy`, `pandas` |
| **Universe Provider** | `providers/sp500_provider.py` | Thu thập 503 mã S&P 500 và 11 GICS ngành từ Wikipedia | `requests`, `pandas`, `lxml` |
| **Market Data Provider**| `providers/yfinance_provider.py` | Tải batch OHLCV daily và FA/Earnings song song (ThreadPoolExecutor) | `yfinance`, `pandas` |
| **Database Schema** | `storage/database.py` | Quản lý kết nối SQLite WAL, khởi tạo bảng và migration an toàn | `sqlite3` |
| **Data Repository** | `storage/repository.py` | Thực thi truy vấn, lưu snapshot, events, signal streaks và outcomes | `sqlite3`, `pandas` |
| **Process Lock** | `storage/lock.py` | File lock bảo vệ pipeline không chạy đè lên nhau | `os`, `pathlib` |
| **Market Breadth** | `analytics/market_breadth.py`| Tính MA20/50/200, ATR14, Dollar Vol, Weekly context, RS Rating | `numpy`, `pandas` |
| **Sector Ranker** | `analytics/sector_ranker.py` | Tính RS 1W/1M/3M, phân loại Leading/Improving/Weakening/Lagging | `pandas` |
| **Industry Ranker** | `analytics/industry_ranker.py`| Xếp hạng 127 nhóm ngành: Day/Wk/Mth/Qtr/6M/1Y, COMP, BLEND, leading stocks | `numpy`, `pandas`, `config` |
| **Screening Rules** | `analytics/screening_rules.py` | Sàng lọc 4 nhóm ứng viên, subtype, gắn nhãn O'Neil Leader, lọc mâu thuẫn | `pandas`, `setup_analyzer` |
| **FA Evaluator** | `analytics/company_fa.py` | Đánh giá tăng trưởng, cảnh báo đòn bẩy, loại trừ ngân hàng, lịch earnings | `pandas` |
| **Update Pipeline** | `jobs/update_pipeline.py` | Điều phối chu trình cập nhật trọn vẹn: fetch -> compute -> snapshot -> events | Toàn bộ providers & analytics |
| **Outcomes Job** | `jobs/update_signal_outcomes.py`| Cập nhật kết quả forward outcomes cho mọi tín hiệu scanner | `repository`, `signal_outcomes` |

---

## 4. Các task đã làm

### [2026-09-14] Khắc Phục Triệt Để 5 Lỗ Hổng Vòng Đời & Dữ Liệu Nền Giá (Bugfix & Hardening) `(EXE)`
- **Mode / Type / Action / Lane:** BUGFIX / REFACTOR / HARDENING / EXECUTE / n/a
- **Tóm tắt:** Khắc phục triệt để toàn bộ 5 lỗi dữ liệu và vòng đời nền giá được phát hiện từ kiểm chứng tái hiện thực tế: (1) Nền đã kết thúc (`played_out`) bị hồi sinh do truy vấn SQLite lọc trạng thái trước khi lấy bản ghi mới nhất; (2) Đếm phiên theo số lần cập nhật thay vì duyệt tuần tự các phiên chưa đánh giá theo lịch giao dịch (khiến nến 8 chỉ đếm là 2 và bỏ sót điểm kết thúc trung gian); (3) Tracker chấp nhận giá NaN/chuỗi lỗi; (4) Chỉ số chất lượng trước breakout bị nhiễm volume phiên breakout; (5) Thiếu dữ liệu sau breakout làm mất danh tính nền do cờ `is_active=False`.
- **Thay đổi chính:**
  1. **Khắc phục Lỗ hổng Truy vấn Nền đã kết thúc (`storage/repository.py`):**
     - Thay thế logic `GROUP BY` / `MAX(id)` bằng Window Function chuẩn SQLite `WITH ranked AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY base_id ORDER BY as_of DESC, id DESC) as rn FROM base_snapshots WHERE base_id IS NOT NULL ...) SELECT * FROM ranked WHERE rn = 1 AND ...`.
     - Đảm bảo luôn lấy bản ghi mới nhất theo đúng thứ tự thời gian `as_of` trước khi lọc trạng thái hoạt động; loại bỏ 100% rủi ro nền `played_out` bị lôi lại snapshot cũ do backfill hoặc out-of-order insertion ID.
  2. **Duyệt Phiên Tuần Tự & Đếm Phiên Lịch Giao Dịch (`analytics/base_detector.py`):**
     - Trong `track_post_breakout_base`, xác định toàn bộ danh sách phiên chưa đánh giá giữa `last_valid_as_of` và phiên hiện tại `as_of`.
     - Chạy vòng lặp duyệt tuần tự từng phiên theo lịch giao dịch: mỗi phiên tăng đúng 1 `bar_count` (từ phiên 1 nhảy đúng sang phiên 8 nếu có 7 nến chưa đánh giá, chuyển `climbing` đúng quy chuẩn).
     - Kiểm tra điều kiện kết thúc chu kỳ (Close < biên dưới hỗ trợ hoặc 2 phiên liên tiếp < MA50) trên từng phiên trung gian và bắt đúng ngày kết thúc `ended_at` ngay tại phiên vi phạm đầu tiên.
     - Bổ sung quét phiên trung gian trong pha forming của `detect_base` để phát hiện kịp thời các ca thủng đáy trung gian.
  3. **Kiểm Tra Tính Hợp Lệ Dữ Liệu OHLCV Tuyệt Đối (`analytics/base_detector.py`):**
     - Đồng bộ ép kiểu số `pd.to_numeric(df[col], errors="coerce")` ngay đầu hàm `detect_base` và `track_post_breakout_base`.
     - Mở rộng cửa sổ kiểm tra n_check tối thiểu 50 phiên; bắt buộc toàn bộ nến phải hữu hạn (`np.isfinite`), giá dương, volume không âm, và thỏa mãn `Low <= Open, Close <= High`.
     - Nếu phát hiện giá trị NaN hoặc vi phạm cấu trúc nến, từ chối tính toán và trả về `data_status="invalid_data"`, không cho phép chuyển sang `fresh_breakout`.
  4. **Tách Bạch Chỉ Số Chất Lượng Nền Tại T-1 Khỏi Nến Breakout (`analytics/base_detector.py`):**
     - Khi xác nhận breakout (`breakout_confirmed`), đóng băng chỉ số co hẹp volume (`vol_contraction`), True Range (`tr_contraction`), ER và cân bằng volume lấy từ snapshot `previous_base` tại T-1.
     - Nếu chạy chế độ fallback không có `previous_base`, tính toán trên cửa sổ 20 phiên kết thúc tại T-1 (`df.iloc[-window_bars - 1 : -1]`), loại trừ hoàn toàn thanh nến breakout tại T. Đồng thời tái tạo mảng `checks` nhất quán tại T-1.
  5. **Bảo Toàn Danh Tính & Vòng Đời Nền Khi Thiếu Dữ Liệu Sau Breakout (`analytics/base_detector.py`):**
     - Mở rộng điều kiện nhận diện nền đang chạy trong `_handle_invalid_or_error`: nhận diện cả các nền có `state in ('breakout_confirmed', 'fresh_breakout', 'climbing')` hoặc `lifecycle_phase in ('fresh_breakout', 'climbing')` kể cả khi `is_active=False`.
     - Giữ nguyên `base_id`, `detected_at`, `state`, `lifecycle_phase`, `upper`, `lower`, các chỉ số chất lượng nền, gán `data_status='insufficient_data'` và ghi chú `last_valid_as_of`, chấm dứt việc trả về `base_id=None, state='none'`.
  6. **Kiểm Thử Toàn Diện (180/180 tests pass 100%):**
     - Xây dựng file kiểm thử chuyên sâu mới `tests/test_base_lifecycle_gap_fixes.py` với 11 test cases bao phủ trọn vẹn 5 ca tái hiện lỗi và các tình huống ngoại lệ biên.
     - Toàn bộ 180 tests trong test suite của hệ thống đều vượt qua.

### [2026-09-14] Rà Soát Độc Lập & Khắc Phục Lỗ Hổng: Quản Lý Vòng Đời Nền Giá, Thay Đổi Trong Phiên & Tooltips 6 Chỉ Số (Review & Bugfix) `(EXE)`
- **Mode / Type / Action / Lane:** REVIEW / BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Rà soát phản biện độc lập toàn diện việc chuyển đổi Base Building sang Thẻ dữ liệu, 6 chỉ số chất lượng và 4 bộ lọc vòng đời sau breakout; phát hiện và khắc phục triệt để lỗi logic truy vấn SQLite làm tê liệt hoàn toàn việc theo dõi sau breakout ở phiên thứ 2, bổ sung trường thay đổi trong phiên (`perf_1d`) còn thiếu, làm giàu tooltips/lý do thiếu dữ liệu và nhãn định thời cho 6 chỉ số, tinh chỉnh bộ lọc/huy hiệu vòng đời và gom nhóm đa nền giá:
  1. **Khắc Phục Lỗ Hổng Chí Mạng Bỏ Sót Nền Sau Breakout (`storage/repository.py`):**
     - Phát hiện: Khi breakout được xác nhận ở phiên 1 (`breakout_confirmed`), `base_detector.py` đặt `is_active = False`. Tuy nhiên, `repo.get_active_post_breakout_bases()` lại truy vấn `WHERE is_active = 1`, dẫn đến việc ở phiên thứ 2 không tìm thấy nền nào để theo dõi tiếp, làm tê liệt hoàn toàn các pha `fresh_breakout` và `climbing`.
     - Khắc phục: Sửa truy vấn trong `get_active_post_breakout_bases()` để lọc theo `(lifecycle_phase IN ('fresh_breakout', 'climbing') OR state IN ('breakout_confirmed', 'fresh_breakout', 'climbing') OR (breakout_date IS NOT NULL AND is_active = 1))` và loại trừ các trạng thái kết thúc (`played_out`, `broken_down`, `lost_structure`).
  2. **Bổ Sung Chỉ Số Thay Đổi Trong Phiên (`perf_1d`) (`analytics/base_detector.py`, `storage/database.py`, `storage/repository.py`, `app/components/base_watchlist.py`):**
     - Yêu cầu ban đầu nêu rõ "Giá đóng cửa, thay đổi trong phiên, ngày dữ liệu", nhưng worker trước chỉ hiển thị giá đóng cửa và ngày dữ liệu.
     - Bổ sung `perf_1d` vào dataclass `BaseResult`, tính toán `% tăng giảm phiên hiện tại so với phiên trước` trong cả `detect_base` và `track_post_breakout_base`.
     - Thực hiện safe migration thêm cột `perf_1d REAL` vào bảng `base_snapshots`, lưu trữ bền vững và hiển thị `Thay đổi: +X.XX%` (có màu xanh/đỏ) trên header thẻ dữ liệu và file CSV xuất ra.
  3. **Làm Giàu Tooltips, Nhãn Định Thời & Lý Do Thiếu Dữ Liệu Cho 6 Chỉ Số (`app/components/base_watchlist.py`):**
     - Bổ sung tooltip chi tiết cho từng chỉ số (công thức toán, cửa sổ dữ liệu, ý nghĩa định lượng đối chiếu phương pháp Banana Patterns).
     - Thay thế nhãn chung chung "N/A" bằng lý do cụ thể: `(Thiếu dữ liệu)`, `(Chưa có Pivot)`, `(Chưa đủ 252 phiên)`.
     - Bổ sung nhãn định thời `[Tại nền]` (frozen trước breakout) và `[Hiện tại]` (giá/pivot/52w phiên hiện tại) cùng banner phân tách thời điểm để xóa bỏ ngộ nhận giữa chỉ số chất lượng nền đóng băng và biến động giá sau breakout.
     - Sử dụng grid layout responsive `minmax(180px, 1fr)` chống tràn vỡ thẻ trên màn hình hẹp/mobile.
  4. **Tinh Chỉnh Huy Hiệu Vòng Đời & Gom Nhóm Thẻ Theo Mã (`app/components/base_watchlist.py`):**
     - Bộ lọc 4 giai đoạn thể hiện rõ đơn vị đếm: `🧱 Đang hình thành (X setup)`, `🚀 Mới bứt phá (Y setup)`, `📈 Tiếp tục tăng (Z setup)`, `🏁 Hoàn tất chu kỳ (W setup)`.
     - Bổ sung ghi chú cảnh báo cho giai đoạn Climbing: "không có nghĩa giá tăng mỗi ngày, cần bám sát MA50/biên hỗ trợ".
     - Pha Forming hiển thị huy hiệu kép: huy hiệu chính `Đang hình thành` đi kèm huy hiệu phụ (`Co chặt`, `Suy yếu`, `Vượt pivot thiếu volume`).
     - Thẻ Played out hiển thị ngày kết thúc và lý do kết thúc chu kỳ (`end_reason`).
     - Gom nhóm nhiều setup của cùng một mã vào chung 1 thẻ bao bì bento duy nhất, không lặp lại thông tin công ty và ngành.
  5. **Mở Rộng Bộ Kiểm Thử Tự Động (166/166 tests pass 100%):**
     - Bổ sung 4 test cases kiểm thử hồi quy mới trong `tests/test_base_lifecycle_and_metrics.py`: tính toán `perf_1d`, truy vấn `get_active_post_breakout_bases` không bị rớt nền confirmed, hiển thị lý do thiếu dữ liệu và gom nhóm thẻ.
     - Toàn bộ 166 tests tự động của hệ thống đều vượt qua trong 20.71s.

### [2026-09-14] Tái Cấu Trúc UX/UI Thẻ Ứng Viên Giao Dịch (Candidate Card Bento Redesign) `(EXE)`
- **Mode / Type / Action / Lane:** REFACTOR / UI / EXECUTE / n/a
- **Tóm tắt:** Nâng cấp toàn diện giao diện Thẻ ứng viên giao dịch (`Candidate Card`) trong `app/components/candidate_cards.py` theo phong cách *Utilitarian Minimalism* chuẩn mực, đóng gói toàn bộ thẻ trong một container thống nhất, bổ sung các mức giá vào lệnh thực chiến, xóa bỏ hoàn toàn trùng lặp dữ liệu báo cáo tài chính và chuẩn hóa hệ thống nút thao tác:
  1. **Hợp nhất Container Đóng Gói (Unified Bento Card):**
     - Đóng gói toàn bộ card từ Header, Body (TA & FA) đến cụm Action trong `with st.container(border=True):`.
     - Khắc phục triệt để lỗi trực quan trước đây khi Header nằm riêng trong thẻ div có viền, còn thân thẻ rớt ra ngoài nền xám và bị chia cắt bởi thẻ `<hr>`.
  2. **Bổ sung Thanh Chỉ Số Vào Lệnh Thực Chiến (Execution & Pricing Bar):**
     - Bổ sung Huy hiệu loại Setup kỹ thuật (`setup_type`, ví dụ: `BREAKOUT 20D`, `PULLBACK MA20`) và mẫu nến trực tiếp tại dòng định danh ticker.
     - Thiết lập thanh chỉ số ngang có nền trung tính `#F9F9F8` và viền nhẹ: Hiển thị đầy đủ Giá hiện tại, biến động 1D/1W/1M, mức kích hoạt (`Trigger`), mức cắt lỗ (`Dừng lỗ / Invalidation`), tỷ lệ rủi ro stoploss (`Rủi ro Stop %`) và biên độ dao động `ATR14`.
  3. **Tối Ưu & Xóa Bỏ Trùng Lặp Cột Bối Cảnh FA (Corporate Context & FA):**
     - Hiển thị ngày công bố BCTC kèm huy hiệu đếm ngược phân loại rủi ro: Xanh nhạt (>14 ngày, `An toàn swing`), Hồng đỏ (<=14 ngày, `Rủi ro biến động gap`).
     - Tinh gọn các cờ cảnh báo thành mini-chips gọn gàng (`⚠️ Doanh thu suy giảm (-3.1% YoY)`, `⚠️ Lợi nhuận suy giảm (-68.6% YoY)`), tự động loại bỏ chuỗi lặp lại `Kỳ kết thúc (MRQ)` bên trong text cảnh báo.
     - Rút gọn metadata xuất xứ thành 1 dòng duy nhất có đường phân cách đứt nét: `Kỳ MRQ` · `Biên ròng` · `Nguồn cấp`, loại bỏ hoàn toàn tình trạng trùng lặp số liệu % và ngày tháng 3 lần trong 4 dòng.
  4. **Chuẩn Hóa Hệ Thống Thao Tác (Action Buttons):**
     - Tăng tỉ lệ cột thao tác lên `2.8/12` (~23.3%) để các nút bấm không bị chèn ép hoặc gãy chữ trên các độ phân giải màn hình khác nhau.
     - Đưa nút trong ứng dụng `Chi tiết {sym} →` thành nút Primary đen nổi bật nhất (thay thế emoji `🔍` bằng mũi tên `→` theo triết lý minimalist).
     - Đồng bộ nút liên kết ngoài với biểu tượng mở tab `↗` (`Chart {sym} ↗`, `Tra cứu SEC ↗`).
- **Files / areas chạm:** `app/components/candidate_cards.py`, `README.md`.
- **Kết quả verify:** 162/162 tests tự động vượt qua (`pytest`, 100% pass bao gồm `test_swing_features.py`, `test_domain_recheck.py`, `test_base_detector.py`, v.v.).

### [2026-09-14] Chuyển Đổi Base Building Sang Thẻ Dữ Liệu 6 Chỉ Số, 4 Bộ Lọc Vòng Đời & Bỏ Biểu Đồ `(EXE)`
- **Mode / Type / Action / Lane:** FEATURE / ANALYTICS / UI / EXECUTE / n/a
- **Tóm tắt:** Chuyển đổi toàn bộ giao diện Base Building ("Đang xây nền") sang dạng Thẻ dữ liệu (Data Cards), bổ sung 6 chỉ số định lượng trọng yếu theo bố cục 2 cột, 4 bộ lọc giai đoạn vòng đời (Forming, Fresh breakouts, Climbing, Played out), loại bỏ biểu đồ nến trong phần này và chia sẻ khối chỉ số sang thẻ ứng viên giao dịch (Candidate Cards):
  1. **Thẻ Dữ Liệu Nền Giá & 6 Chỉ Số Định Lượng (`app/components/base_watchlist.py`):**
     - Thay thế hoàn toàn bảng dữ liệu và biểu đồ nến bằng các Thẻ ứng viên (Candidate Data Cards).
     - Phần đầu thẻ: Mã cổ phiếu, Tên doanh nghiệp, Ngành / Phân ngành, Giá đóng cửa, Ngày dữ liệu, Huy hiệu trạng thái và Lý do kết thúc (nếu có).
     - Dòng tóm tắt chuẩn hóa: `Nền đi ngang · 20 phiên / khoảng 4 tuần · sâu …% · Pivot $….`
     - Bố cục 2 cột với 6 chỉ số trọng yếu:
       - Cột trái: `RS rating (1-99)`, `Now vs pivot (%)`, `Tightening (ATR ratio)` (tỷ số True Range trung bình 10 phiên cuối / 10 phiên đầu).
       - Cột phải: `Volume dry-up` (tỷ số Volume trung bình 10 phiên cuối / 10 phiên đầu), `Up/down volume, net` (cân bằng khối lượng tăng/giảm [-1.0, +1.0]), `From 52-week high` (khoảng cách từ đỉnh 52 tuần cao nhất, yêu cầu tối thiểu 252 phiên).
     - Expander chi tiết kỹ thuật: Biên trên/dưới, độ rộng nền, Center shift, ER, cửa sổ 20 phiên, phát hiện ban đầu, bối cảnh MA50/MA200, áp lực giá-volume, checklist 6 tiêu chuẩn, và bảng lịch sử các nền giá trước đây của mã.
     - Giữ lại helper `_create_base_figure` ở mức private để tương thích ngược 100% với các bài test hồi quy, nhưng không render biểu đồ nến trong giao diện.
  2. **4 Bộ Lọc Vòng Đời Nền Giá (Lifecycle Filters):**
     - 4 bộ lọc trực quan dạng segmented control / box:
       - `Forming` (Mặc định): Nền đang hình thành trong biên (`forming`, `tight`, `breakout_unconfirmed`, `weakening`).
       - `Fresh breakouts`: Mới bứt phá, từ phiên 1 đến 5 sau breakout (`fresh_breakout`, `breakout_confirmed`).
       - `Climbing`: Tiếp tục tăng, từ phiên thứ 6 trở đi sau breakout (`climbing`).
       - `Played out`: Hoàn tất chu kỳ sau breakout khi chạm điều kiện thoát (Close < biên dưới hỗ trợ hoặc 2 phiên liên tiếp đóng cửa dưới MA50).
     - Các nền thất bại trước breakout (`broken_down`, `lost_structure`) được bảo lưu trong lịch sử nền của mã với lý do thất bại, không bị phân loại nhầm vào `Played out`.
     - Bộ lọc tìm kiếm và ngành áp dụng đồng nhất cho bộ đếm số lượng của 4 hộp lọc, danh sách thẻ hiển thị và file CSV xuất ra.
  3. **Động Cơ Theo Dõi Vòng Đời Sau Breakout (`analytics/base_detector.py`):**
     - Bổ sung hàm `track_post_breakout_base`: Đóng băng các đặc tính của nền cũ, theo dõi bước nhảy phiên (`breakout_bar_count`), kiểm soát chuỗi đóng cửa dưới MA50 (`consecutive_below_ma50`).
     - Ưu tiên điều kiện kết thúc chu kỳ: Nếu Close < biên dưới hoặc 2 phiên < MA50, chuyển ngay sang `played_out` kể cả khi đang ở phiên 1-5.
     - Bảo toàn trạng thái an toàn: Dữ liệu thiếu/cũ (`stale_data`) hoặc chạy lại cùng phiên (idempotent) không tăng số phiên hay tạo bước nhảy giả.
  4. **Nâng Cấp Cơ Sở Dữ Liệu & Repository (`storage/database.py`, `storage/repository.py`):**
     - Mở rộng bảng `base_snapshots` với 12 cột mới: `lifecycle_phase`, `rs_rating`, `high_52w`, `from_52w_high_pct`, `now_vs_pivot_pct`, `breakout_date`, `breakout_price`, `breakout_bar_count`, `consecutive_below_ma50`, `ended_at`, `end_reason`, `formula_version`.
     - Bổ sung `get_active_post_breakout_bases(before_date)` để truy xuất các nền đang chạy sau breakout (`fresh_breakout`, `climbing`).
     - Bổ sung `get_base_history_by_symbol(symbol, as_of)` truy xuất lịch sử nền point-in-time không rò rỉ dữ liệu tương lai.
  5. **Tích Hợp Pipeline Cập Nhật (`jobs/update_pipeline.py`):**
     - Truyền `rs_ratings_map` từ `latest_stocks_df` vào detector để lưu trữ RS rating (1-99).
     - Kết hợp theo dõi cả nền sau breakout đang chạy lẫn quét nền mới trong phiên EOD.
  6. **Tích Hợp Khối 6 Chỉ Số Sang Candidate Cards (`app/components/candidate_cards.py`):**
     - Xuất hàm `render_base_metrics_grid` và `format_base_summary_line` dùng chung.
     - Khi một ứng viên giao dịch (Long/Short Continuation, Reversal, Watchlist) có nền giá tương ứng trong snapshot hoặc local DB, tự động hiển thị khối 6 chỉ số và dòng tóm tắt nền ngay trên thẻ ứng viên.
  7. **Kiểm Thử Toàn Diện (162 tests pass 100%):**
     - Bổ sung `tests/test_base_lifecycle_and_metrics.py` (14 tests) bao phủ tính toán 6 chỉ số, chuyển dịch vòng đời 1-5 -> 6, ưu tiên kết thúc, phân tách pre-breakout failure, chống rò rỉ tương lai và an toàn UI khi thiếu dữ liệu.
     - Toàn bộ 162 bài kiểm thử tự động của hệ thống đều vượt qua.

### [2026-09-12] Bổ Sung Tính Năng Nhận Diện “Đang Xây Nền” (Base Building Watchlist) & Bằng Chứng Tích Lũy `(EXE)`
- **Mode / Type / Action / Lane:** FEATURE / ANALYTICS / UI / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn mục “Đang xây nền” trong trang Ứng viên (Pillar 1) giúp phát hiện cổ phiếu trước khi breakout bằng nến ngày đã đóng và universe S&P 500:
  1. **Cơ chế Nhận diện Định lượng (`analytics/base_detector.py`):**
     - Tách bạch cấu trúc hình học của nền khỏi bằng chứng tích lũy khối lượng.
     - Cửa sổ nền chuẩn 20 phiên, yêu cầu tối thiểu 40 phiên hợp lệ liên tiếp (41 phiên để tính True Range đầy đủ).
     - Tiêu chí nền hẹp: Độ rộng `(đỉnh nền - đáy nền) / đáy nền <= 12.0%`.
     - Tiêu chí dao động đi ngang: Hiệu suất dịch chuyển `ER = |Close_T - Close_0| / Path <= 0.35`.
     - Tiêu chí ổn định tâm giá: Độ lệch tâm 2 nửa nền `Center Shift = |Mean(Close_sau) - Mean(Close_trước)| / Range <= 0.30`. Loại bỏ hiệu quả các hình thái tăng/giảm đều hoặc nảy chữ V.
     - Phân loại **Nền co chặt (Tight Base)**: Đạt thêm co hẹp True Range (`TR_sau / TR_trước <= 0.80`) và volume cạn kiệt (`Vol_sau / Vol_trước <= 0.80`).
  2. **Quản lý Đợt Nền & Vòng Đời Trạng Thái (Lifecycle State Machine):**
     - Khi phát hiện nền lần đầu, gán mã định danh `base_id = f"{symbol}:{detected_at}:{rule_version}"` và **cố định (đóng băng) biên trên/dưới**. Mức breakout/thủng nền kiểm tra ở phiên T sử dụng biên đã biết từ T-1, không kéo biên theo nến mới.
     - Quản lý các trạng thái: `forming` (đang xây nền), `tight` (nền co chặt), `breakout_unconfirmed` (vượt biên trên nhưng volume < 1.2x SMA20 vol), `breakout_confirmed` (vượt biên trên kèm volume >= 1.2x SMA20 vol), `broken_down` (thủng biên dưới), `weakening` (suy yếu trong biên), `lost_structure` (kết thúc đợt sau 2 phiên suy yếu liên tiếp).
     - Râu nến vượt biên nhưng Close quay lại nền được ghi nhận là kiểm định biên (upper/lower probe / wick test); nến breakout không xác nhận quay lại nền được ghi chú "vượt nền rồi quay lại".
     - Quy tắc đóng đợt: Sau khi breakout xác nhận, thủng nền hoặc mất cấu trúc, nền được đóng; nền mới phải có cửa sổ 20 phiên bắt đầu sau ngày kết thúc đợt cũ.
     - Không ép vị trí trong nền `position` về `[0, 1]` (cho phép > 100% khi breakout hoặc < 0% khi thủng).
  3. **Bằng Chứng Tích Lũy & Bối Cảnh (Accumulation Evidence):**
     - Chỉ số cân bằng volume theo chiều Close (`signed_volume_balance` trên 20 phiên nền): phân loại minh bạch thành "Volume thuận" (>0.10), "Volume mâu thuẫn" (<-0.10), và "Cân bằng", không gán ghép là tỷ lệ mua bán thực tế.
     - Nhãn bối cảnh xu hướng độc lập: "Nền trong xu hướng tăng" (`Close > MA50` và `MA50_T >= MA50_T-5`), "Nền trong xu hướng giảm" (`Close < MA50` và `MA50_T < MA50_T-5`), hoặc "Trung tính".
     - Tuyệt đối không hiển thị điểm số dưới dạng xác suất tăng giá.
  4. **Cơ Sở Dữ Liệu & Cách Ly Outcomes (`storage/database.py`, `storage/repository.py`):**
     - Bổ sung bảng `base_snapshots` (với khóa ngoại `snapshot_id`) lưu trữ đầy đủ biên nền, trạng thái, vị trí, ER, co hẹp TR/Vol, bằng chứng volume và checklist JSON.
     - Lưu riêng biệt hoàn toàn với `candidate_snapshots`, đảm bảo engine Outcomes không tự tạo bản ghi lợi suất Long cho các mã chỉ đang xây nền.
     - Snapshot cũ chưa có dữ liệu hiển thị thông báo "chưa tính" an toàn.
  5. **Dòng Sự Kiện Biến Động Nền (`analytics/signal_events.py`):**
     - Phát sinh sự kiện khi trạng thái nền thay đổi (`base_forming`, `base_tight`, `base_breakout_unconfirmed`, `base_breakout_confirmed`, `base_broken_down`, `base_lost_structure`).
     - Khóa sự kiện duy nhất `event_key = f"{as_of}:{base_id}:{event_type}"` đảm bảo chạy lại cùng phiên không nhân đôi cảnh báo.
  6. **Tích Hợp Pipeline & Làm Giàu FA (`jobs/update_pipeline.py`):**
     - Quét toàn bộ cổ phiếu đồng phiên (fresh) của vũ trụ S&P 500 để phát hiện nền giá.
     - Bổ sung các mã đang xây nền vào danh sách ưu tiên làm giàu dữ liệu FA và lịch công bố BCTC.
  7. **Giao Diện Người Dùng Chuyên Nghiệp (`app/components/base_watchlist.py`, `app/main.py`, `app/components/candidate_cards.py`):**
     - Thêm mục `🧱 Đang Xây Nền` tại điều hướng Pillar 1 và trong các nhóm ứng viên swing.
     - Thẻ chỉ số tổng quan (Nền co chặt, Đang xây nền, Vượt nền thiếu vol, Breakout xác nhận, Thủng nền).
     - Bộ lọc linh hoạt theo trạng thái và 11 ngành GICS; tìm kiếm mã; xuất dữ liệu CSV.
     - Bảng chi tiết ghi rõ riêng biệt "Cửa sổ nền 20 phiên" và "Phát hiện từ ngày..." tránh ngộ nhận nền thực sự bắt đầu đúng 20 phiên trước.
     - Biểu đồ nến Plotly tích hợp vùng tô bóng (shaded rectangle) trực quan cho 20 phiên nền, 2 đường biên ngang đóng băng (Xanh: Kháng cự biên trên, Đỏ: Hỗ trợ biên dưới) và khối lượng kèm SMA20 vol.
     - Checklist định lượng 6 tiêu chí Pass/Fail rõ ràng kèm link 1-click TradingView.
  8. **Hiệu Chỉnh Mô Tả Near Breakout (`analytics/screening_rules.py`):**
     - Sửa diễn giải `near_breakout` để chỉ mô tả sự thật kỹ thuật đã kiểm tra (giá sát đỉnh 20 phiên trong biên 1.5% kèm volume đạt chuẩn), chấm dứt suy diễn chủ quan về việc "đang tích lũy".
  9. **Bộ Tứ Sửa Lỗi Tinh Chỉnh & Phòng Vệ (Edge Case Hardening):**
     - **Cắt nến Point-in-time trên Biểu đồ (`app/components/base_watchlist.py`):** Lọc nghiêm ngặt `date <= as_of` trước khi lấy 60 nến cuối, loại bỏ triệt để hiện tượng snapshot lịch sử (ví dụ 31/07) hiển thị nến tương lai.
     - **Xác thực OHLC & Liên tục Lịch Thị trường (`analytics/base_detector.py`):** Kiểm tra `Low <= Open, Close <= High`, loại bỏ ngày trùng lặp và phát hiện khoảng trống ngày giao dịch bị thiếu (`get_trading_days`), trả về `invalid_data`/`insufficient_data`. Đồng thời bảo toàn toàn bộ chỉ số định lượng/checklist của nền cũ khi gặp dữ liệu lỗi/stale.
     - **Giới hạn Vũ trụ Cổ phiếu S&P 500 (`jobs/update_pipeline.py`):** Dùng `fresh_sp500` cho bộ quét nền mới và loại bỏ triệt để benchmark (`SPY`, `RSP`) cùng Sector ETFs khỏi danh sách phát hiện nền lẫn hàng đợi ưu tiên cập nhật FA.
     - **Bảo tồn Nền Stale & Phục hồi Sự kiện Chuyển Trạng thái (`jobs/update_pipeline.py`, `analytics/signal_events.py`):** Mang tiếp các nền đang hoạt động khi mã bị thiếu dữ liệu ở phiên hiện tại với trạng thái `stale_data`; đối chiếu `base_id` với snapshot nền gần nhất để không bỏ sót cảnh báo breakout/thủng nền/mất cấu trúc khi dữ liệu phục hồi.
- **Files / areas chạm:** `config/settings.py`, `analytics/base_detector.py`, `analytics/signal_events.py`, `analytics/screening_rules.py`, `storage/database.py`, `storage/repository.py`, `jobs/update_pipeline.py`, `app/components/base_watchlist.py`, `app/components/candidate_cards.py`, `app/main.py`, `tests/test_base_detector.py`, `tests/test_base_fixes_regression.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite dự án: `pytest` đạt **145/145 tests pass 100%** trong 13.05s (trong đó có 24 tests trong `test_base_detector.py` và 13 tests chuyên sâu trong `test_base_fixes_regression.py`).
  - Kiểm thử chấp nhận hoàn thành: Nhận đúng fixture đi ngang; loại chuỗi tăng/giảm đều dù biên độ hẹp; loại nến sai OHLC (`Open=1000`) và thiếu phiên giữa cửa sổ; biểu đồ snapshot cũ không rò rỉ nến tương lai; loại trừ hoàn toàn ETF/SPY khỏi quét nền; lưu giữ nền stale an toàn và phát sinh đúng sự kiện khi phục hồi; snapshot cũ hiển thị "chưa tính".

### [2026-09-12] Đồng Bộ Light Theme Cho Cụm Biểu Đồ 3 Chỉ Số & Thẻ Đối Chiếu Tỷ Lệ `(EXE)`
- **Mode / Type / Action / Lane:** UI_STYLING / REFINEMENT / EXECUTE / n/a
- **Tóm tắt:** Chuyển đổi toàn bộ bảng màu từ Dark Theme sang Light Theme đồng bộ tuyệt đối với ngôn ngữ thiết kế utilitarian minimalist của toàn bộ ứng dụng Market Radar:
  1. **Cụm Biểu đồ 3 Chỉ số Lớn (`app/components/index_charts.py`):**
     - Chuyển `paper_bgcolor` và `plot_bgcolor` sang nền trắng `#FFFFFF`, đường lưới tọa độ xám siêu nhẹ `#F1F5F9`, nhãn số trục x/y `#64748B`.
     - Sử dụng `st.container(border=True)` bao bọc nguyên khối thẻ biểu đồ với viền `#EAEAEA` bo góc 6px và đổ bóng nhẹ.
     - Tiêu đề chỉ số đen sâu `#111111`, huy hiệu giá đóng cửa màu vàng hổ phách nhạt thanh lịch (`#FEF08A` chữ `#854D0E` viền `#FDE047`).
     - Thanh Relative Volume màu xanh hoàng gia `#2563EB`, nến tăng xanh `#16A34A` và nến giảm đỏ `#DC2626`.
  2. **5 Thẻ Đối Chiếu Tỷ Lệ (`app/components/metrics_cards.py`):**
     - Nền thẻ trắng `#FFFFFF`, viền mỏng `#EAEAEA`, đổ bóng vi tế `box-shadow: 0 1px 2px rgba(0,0,0,0.02)`.
     - Tỷ lệ phần trăm xanh lá `#15803D` và đỏ thẫm `#B91C1C` tương phản rõ nét trên nền trắng, số lượng mã muted xám tro `#64748B`.
     - Rãnh trượt tiến độ nền xám nhạt `#F1F5F9` kết hợp thanh bar 2 màu xanh/đỏ phân định rõ rệt.
     - Huy hiệu `SMA50`/`SMA200` và `BULL %`/`BEAR %` chuyển sang tone pastel viền mỏng tinh tế (`#DCFCE7` / `#FEE2E2`).
  3. **CSS Toàn Cục (`app/main.py`):**
     - Bổ sung cấu hình CSS cho `div[data-testid="stVerticalBlockBorderWrapper"]` bảo đảm mọi container viền đồng nhất nền `#FFFFFF` và viền `#EAEAEA`.
- **Verify:** `pytest tests/ -v` đạt **108/108 tests PASS (100%)** trong 21.64s.

### [2026-09-12] Nâng Cấp Giao Diện: Biểu Đồ 3 Chỉ Số Lớn, Thanh Bar Đối Chiếu Tỷ Lệ & Phân Hệ Earnings Calendar `(EXE)`
- **Mode / Type / Action / Lane:** UI_UPGRADE / FEATURE / EXECUTE / n/a
- **Tóm tắt:** Hoàn thành trọn vẹn 3 nâng cấp giao diện theo yêu cầu người dùng và ảnh đối chiếu (Hình 1, Hình 2):
  1. **[M19] Cụm Biểu Đồ 3 Chỉ Số Lớn (`app/components/index_charts.py`):**
     - Hiển thị 3 thẻ đặt cạnh nhau cho **S&P 500 (`^GSPC`)**, **NASDAQ (`^IXIC`)**, **DOW (`^DJI`)** theo phong cách Bloomberg/Finviz.
     - Tên chỉ số, ngày phiên (`Sep 11`), bước nhảy điểm và phần trăm tăng giảm (+/-) có màu xanh/đỏ rõ ràng.
     - Huy hiệu giá chốt phiên nổi bật với nền vàng (`#EAB308`) và font chữ `Geist Mono` đậm.
     - Biểu đồ nến Nhật Plotly sắc nét với vạch ngang màu đỏ chấm chấm (`dash="dot"`) thể hiện giá đóng cửa phiên trước (`prev_close`).
     - Cột đo lường thanh khoản tương đối (Relative Volume Bar) ở mép trái với các mốc 0.5, 1.0, 1.5, 2.0.
     - Hỗ trợ chuyển đổi linh hoạt giữa **Intraday (Nến 5m phiên gần nhất)** và **Daily (Nến ngày 30 phiên)** với cơ chế cache `@st.cache_data(ttl=300)` chống nghẽn mạng.
  2. **[M20] Thẻ Thanh Bar Đối Chiếu Tỷ Lệ Độ Rộng Thị Trường (`app/components/metrics_cards.py`):**
     - Thay thế 4 thẻ `st.metric` đơn điệu cũ bằng các thẻ đối chiếu tỷ lệ có thanh bar phân tách hai màu (Xanh / Đỏ) co giãn linh hoạt:
       - **Advancing vs Declining:** Tỷ lệ % và số lượng mã tăng/giảm (VD: `67.8% (341)` vs `(162) 32.2%`).
       - **New High vs New Low (Đỉnh/Đáy 20P):** Tỷ lệ và số lượng cổ phiếu tiệm cận biên 0.5% đỉnh/đáy 20 phiên.
       - **Above vs Below SMA50:** Huy hiệu trung tâm `SMA50`, tỷ lệ % và số lượng mã trên/dưới MA50 ngày.
       - **Above vs Below SMA200:** Huy hiệu trung tâm `SMA200`, tỷ lệ % và số lượng mã trên/dưới MA200 ngày.
       - **Xung Lực & Net Breadth (Bull/Bear):** Thẻ thứ 5 thể hiện xung lực thị trường với tỷ lệ `BULL %` và `BEAR %` kèm mức Net Breadth điểm phần trăm.
  3. **[M21] Phân Hệ Lịch Báo Cáo Tài Chính - Earnings Calendar (`app/components/earnings_calendar.py` & `providers/yfinance_provider.py`):**
     - Bổ sung phương thức `fetch_earnings_calendar` vào `YFinanceProvider` khai thác `yf.Calendars().get_earnings_calendar()` có cache kết hợp cơ sở dữ liệu `fundamentals` làm fallback an toàn.
     - Xây dựng giao diện trạm làm việc Lịch BCTC chuyên nghiệp tại Pillar 1 (`03 Lịch Báo Cáo Tài Chính (Earnings) 📅`):
       - Bộ lọc thời gian: Tuần này, Tuần tới, 14 ngày tới, 30 ngày tới, hoặc Tùy chọn khoảng ngày.
       - Bộ lọc phạm vi: Toàn bộ thị trường vs S&P 500 vs ⭐ Chỉ Ứng viên Radar.
       - Bộ lọc thời điểm công bố: Trước giờ mở cửa (BMO ☀️) vs Sau giờ đóng cửa (AMC 🌙) vs TNS.
       - Hai chế độ hiển thị: **📅 Lịch Tuần (Weekly Schedule)** dạng thẻ cột ngày và **📋 Bảng Dữ Liệu Chi Tiết (Full Interactive Table)**.
       - Tích hợp liên kết nhanh 1-click mở biểu đồ **TradingView** và hồ sơ **SEC EDGAR 10-Q/8-K**.
  4. **Tích hợp Điều hướng & Trải nghiệm Người dùng (`app/main.py`, `app/components/today_dashboard.py`):**
     - Cụm 3 chỉ số lớn được đặt trang trọng ngay đầu trạm *Bức Tranh Thị Trường*.
     - Bổ sung thông báo định hướng từ tab BCTC trên trang *Hôm Nay* sang trạm *Lịch BCTC* toàn diện.
  5. **Sửa Lỗi Hiển Thị HTML & Tinh Gọn Biểu Đồ Chỉ Số (Bugfix & Hardening):**
     - Thay thế `st.markdown(..., unsafe_allow_html=True)` bằng `st.html()` (hàm `render_html_safe`) và loại bỏ toàn bộ thụt lề 4 space trong các chuỗi template HTML để triệt tiêu hoàn toàn lỗi Python-Markdown biến code HTML thành `<pre><code>` block.
     - Tái cấu trúc cụm biểu đồ 3 chỉ số lớn trong `index_charts.py` bằng `make_subplots` của Plotly (cột trái: Relative Volume Meter, cột phải: Nến Nhật + đường tham chiếu đỏ), loại bỏ các sub-columns lồng nhau của Streamlit gây vỡ bố cục trên màn hình hẹp.
  6. **Bộ Kiểm thử Tự Động & Hồi quy:**
     - Viết mới `tests/test_index_charts.py` và `tests/test_earnings_and_contrast.py`.
     - Toàn bộ test suite chạy thành công đạt **108/108 tests pass 100%** trong 18.81s.
- **Files / areas chạm:** `app/components/index_charts.py`, `app/components/metrics_cards.py`, `app/components/earnings_calendar.py`, `providers/yfinance_provider.py`, `app/main.py`, `app/components/today_dashboard.py`, `tests/test_index_charts.py`, `tests/test_earnings_and_contrast.py`, `README.md`.
- **Verify:**
  - `pytest tests/ -v`: **108 passed** (100%) trong 18.81s.
  - Compile kiểm tra cú pháp toàn bộ project: sạch 100%.

### [2026-09-12] Khắc Phục Triệt Để 6 Điểm Nghẽn Miền & Khôi Phục Tính Toàn Vẹn Dữ Liệu Lịch Sử (Domain Recheck & Migration) `(EXE)`
- **Mode / Type / Action / Lane:** DOMAIN / DATA_MIGRATION / BUGFIX / EXECUTE / n/a
- **Tóm tắt:** Hoàn thiện triệt để 6 lỗ hổng miền tài chính và cơ sở dữ liệu theo tài liệu rà soát `docs/domain-recheck-2026-09-11.md`:
  1. **[R-01] Phân tách Xuất xứ Sự kiện (Event Provenance Separation):** Tách dứt khoát sự kiện thuật toán scanner EOD (`analytic_event`, nguồn: `Market Radar Scanner (EOD OHLCV)`, link TradingView, status `scanner_derived`) khỏi sự kiện doanh nghiệp bên ngoài (`external_company_event`, nguồn: `Yahoo Finance Calendar (Ước tính / Estimate)`, status `Chưa kiểm tra (Unverified / Ước tính)`, nút tra cứu SEC EDGAR kèm cảnh báo). Chấm dứt hoàn toàn việc gán mác SEC EDGAR giả mạo cho các sự kiện kỹ thuật nội bộ (`new_candidate`, `setup_triggered`, `sector_rank_shift`).
  2. **[R-02] Minh bạch Hợp đồng Dữ liệu Cơ bản (FA Metadata Contract):** Bổ sung trường `period_end` và `retrieved_at` vào bảng `fundamentals` và module FA; công bố rõ nguồn cấp là số liệu tổng hợp (`Yahoo Finance (Số liệu tổng hợp / Aggregate)`), không giả mạo đã trích xuất trực tiếp từ hồ sơ 10-Q/10-K; gắn cờ cảnh báo BCTC cũ lạc hậu (`is_stale`) khi `period_end > 180` ngày so với ngày phân tích.
  3. **[R-03] Migration & Backfill Toàn diện Dữ liệu Lịch sử:** Xây dựng script `jobs/backfill_legacy_data.py` (tạo bản sao lưu an toàn `data/market_radar.db.bak`):
     - Xóa sạch 100% tỷ lệ NULL trên 167 bản ghi `fundamentals` (`fiscal_period`, `period_end`, `sec_filing_url`).
     - Chuẩn hóa toàn bộ 170 sự kiện `signal_events` (0% claim SEC sai lệch).
     - Bổ sung hồ sơ áp lực đa phiên `evidence_json` cho 340 ứng viên scanner.
     - Lấp đầy 1.360 dòng forward outcomes cho đủ 8 khung kỳ hạn (1, 2, 3, 4, 99-week-close, 5, 10, 20 phiên) trên mọi đợt tín hiệu đã ghi nhận.
     - Phục hồi snapshot 3 (gắn nhãn `legacy_incompatible`), snapshot 1-2 (`legacy`), và tạo snapshot 4 chuẩn mực (`valid_universe = 503`, `total_universe = 503`, `coverage_252d = 99.2%`, `status = 'complete'`).
  4. **[R-04] Fail-closed Snapshot Status & Khắc phục Ngưỡng Coverage 252 Phiên:**
     - Sửa lỗi logic tỷ lệ bao phủ lịch sử 1 năm tại `jobs/update_pipeline.py`: chuyển từ ngưỡng cứng `>= 253` bars (khiến coverage về 0% dù đủ 252 phiên/năm của Yahoo) sang `>= 250` bars -> phục hồi tỷ lệ bao phủ đạt chuẩn 99.2% (499/503 mã).
     - Siết chặt bất biến vũ trụ: `valid_universe = min(fresh_count, total_sp500)`, chấm dứt việc gộp 13 ETF làm sai lệch `valid_universe > total_universe`.
     - Cơ chế Fail-Closed trên giao diện UI (`app/main.py`): Khi phát hiện snapshot cũ vi phạm bất biến hoặc quá cũ, hiển thị cảnh báo `Lỗi Bất Biến (Legacy)` / `Cũ (X phiên)` thay vì gắn mác xanh "Hoàn tất"; hiển thị banner giải thích tính tương thích cho snapshot cũ.
  5. **[R-05] Loại bỏ Triệt để Ngôn ngữ Gán Ý chí Chủ quan (Causal Intent Vocabulary):** Viết lại toàn bộ câu chữ thông dịch nến và áp lực đa phiên trong `setup_analyzer.py`; thay thế các suy diễn "lực cầu hấp thụ tốt", "phe bán áp đảo" bằng sự thật quan sát được về giá - volume ("giá đóng cửa gần đỉnh phiên", "biên độ hẹp kèm thanh khoản thấp", "bằng chứng thuận cho phía mua", "bằng chứng mâu thuẫn cho phía bán").
  6. **[R-06] Bộ Kiểm thử Chấp nhận & Hồi quy Chuyên sâu:** Xây dựng `tests/test_domain_recheck.py` với 9 kiểm thử tự động kiểm tra toàn bộ 5 yêu cầu R-01 -> R-05; chạy toàn bộ test suite đạt **95/95 tests pass 100%**.
- **Files / areas chạm:** `analytics/signal_events.py`, `app/components/today_dashboard.py`, `providers/yfinance_provider.py`, `storage/database.py`, `storage/repository.py`, `analytics/company_fa.py`, `app/components/setup_detail.py`, `app/components/candidate_cards.py`, `analytics/setup_analyzer.py`, `jobs/update_pipeline.py`, `jobs/backfill_legacy_data.py`, `app/main.py`, `tests/test_domain_recheck.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest tests/ -v` đạt **95/95 tests pass 100%** trong 22.80s.
  - Bytecode compile toàn bộ dự án không có bất kỳ lỗi cú pháp nào: `python -m compileall app/ analytics/ storage/ providers/ jobs/ config/ tests/`.
  - Kiểm tra database thực tế: 0 NULL trong `fiscal_period`, `period_end`, `sec_filing_url`; 0 sự kiện scanner claim SEC; 1.360 dòng forward outcomes đủ 8 kỳ hạn; snapshot 3 được cô lập thành `legacy_incompatible`.

### [2026-09-11] Khắc Phục Triệt Để 4 Lỗ Hổng: Crash MA50, Lệch Phiên ETF, Gap Lịch 1D & Bỏ Sót Mã Thiếu Bar (Bugfix) `(EXE)`
- **Mode / Type / Action / Lane:** BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Khắc phục triệt để 4 lỗi tiềm ẩn và đồng bộ khung thời gian ma trận phụ trợ theo phản hồi nghiệm thu:
  1. [P1] Sửa lỗi crash `TypeError` trên trang ngành khi một ngành thiếu MA50 (`sector_table.py:68`): lọc an toàn các giá trị hợp lệ trước khi tìm max; nếu toàn bộ thiếu hiển thị `"N/A"`; đồng thời bọc an toàn toàn bộ so sánh và format chuỗi cho `top5_concentration_pct`, `turnover_est`, `close`, `volume`, `share_in_sector`.
  2. [P1] Xử lý stale ETF trong luân chuyển ngành (`sector_rotation.py:125, 216`): đối chiếu ngày cuối của từng ETF với phiên mục tiêu SPY; gắn nhãn `"Chưa xác minh (Dữ liệu cũ / Lệch phiên)"`, gán `is_stale = True`, `rank = None`, `is_ranked = False` và loại khỏi xếp hạng hiện tại; đồng bộ cơ chế này sang `sector_ranker.py` để ngăn ETF lệch phiên lọt vào Top 1 dẫn đầu.
  3. [P2] Khắc phục tính gộp lợi suất đa phiên khi thiếu nến (`market_participation.py:111`, `sector_rotation.py:187`): xây dựng trục lịch giao dịch chuẩn (`calendar_sessions` spine); bắt buộc phải có giá của đúng phiên liền kề ($t-1$); nếu bị thiếu (gap lịch), lợi suất 1D trả về `None` và loại khỏi mẫu số tính breadth/equal-weight/median return.
  4. [P2] Bổ sung mã thiếu bar vào coverage lịch sử (`market_participation.py:85, 139`): đối chiếu với universe kỳ vọng (`expected_count`), phân tách rõ ràng `expected_count`, `bars_count` và `missing_bars_count`, không để tình trạng mã mất bar bị báo `missing_count = 0`.
  5. Đồng bộ cửa sổ Ma trận Bổ trợ (`sector_table.py:206`): chuyển sang cùng cửa sổ 1D (`Net Breadth 1D` vs `Lợi suất ETF 1D`), loại bỏ các hàng thiếu dữ liệu để giữ nguyên `N/A` thay vì vẽ điểm giả tại `(0, 0)`.
- **Files / areas chạm:** `app/components/sector_table.py`, `analytics/sector_rotation.py`, `analytics/sector_ranker.py`, `analytics/market_participation.py`, `analytics/market_breadth.py`, `tests/test_sector_table.py`, `tests/test_sector_rotation.py`, `tests/test_market_participation.py`, `tests/test_analytics.py`, `README.md`, `SRS.md`.
- **Verify:**
  - `pytest -v` đạt **78/78 tests pass 100%** (15 unit/regression tests mới cho 4 ca lỗi và ma trận).
  - Tái hiện và xác nhận fix crash `sector_table`: chạy test với `breadth_ma50_pct = None` và `turnover_est = None` -> Render trơn tru, hiển thị `N/A`.
  - Tái hiện và xác nhận fix stale ETF: XLK kết thúc trước SPY 14 ngày -> cả rotation và ranker đều gán `Chưa xác minh (Dữ liệu cũ / Lệch phiên)` và unranked.
  - Tái hiện và xác nhận calendar gap: STK thiếu phiên thứ Ba -> thứ Tư không tính lợi suất 2 ngày vào 1D, `equal_weight_return` và `median_return` chỉ tính trên mã hợp lệ.
  - Tái hiện và xác nhận coverage: universe 2 mã nhưng chỉ 1 mã có bar -> `missing_count = 1`, `coverage_pct = 50.0%`.

### [2026-09-10] Nâng Cấp Toàn Diện Bản Đồ Thị Trường & Ngành: Độ Rộng Tham Gia, Thanh Khoản & Luân Chuyển Ngành (EXE)
- **Mode / Type / Action / Lane:** FEATURE / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn 5 bước nâng cấp theo kế hoạch phân tích độ rộng, thanh khoản và luân chuyển ngành EOD trên nền tảng S&P 500, Streamlit, SQLite và dữ liệu mở 0đ:
  1. Chuẩn hóa quy tắc xử lý dữ liệu: phân biệt mã đứng giá (unchanged) vs thiếu dữ liệu, tính độ rộng MA20/50/200 với mẫu số chỉ gồm các mã có đủ dữ liệu quan sát (loại trừ mã thiếu MA khỏi mẫu số), RVOL 20 phiên chuẩn nhân quả không lookahead, công bố rõ ràng GTGD ước tính (`close * volume`) do giá điều chỉnh và AD Volume là khối lượng cổ phiếu tăng/giảm (không phóng đại intraday CVD).
  2. Xây dựng module phân tích độ rộng tham gia và chuỗi thời gian thị trường (`analytics/market_participation.py`): Net Breadth, đường A/D lũy kế, đường AD Volume lũy kế & %, lịch sử độ rộng MA20/50/200, so sánh lợi suất Equal-Weight vs Median.
  3. Phân tích luân chuyển ngành 4 góc phần tư có vệt lịch sử 10 phiên (`analytics/sector_rotation.py`): tính theo công thức chuẩn hóa $X_t = 100 \times (R_t / EMA_{20}(R)_t - 1)$ và $Y_t = X_t - X_{t-5}$, kết hợp nhãn xu hướng tuyệt đối (Bullish/Bearish); lọc dữ liệu point-in-time theo `as_of`.
  4. Tách biệt sức khỏe nội bộ ngành: phát hiện phân kỳ méo mó do cổ phiếu vốn hóa lớn (mega-cap divergence), đo lường tỷ trọng GTGD ngành, biến động tỷ trọng 5 phiên và mức độ tập trung thanh khoản Top 5 mã.
  5. Nâng cấp lưu trữ và giao diện Streamlit: Safe migration mở rộng bảng `snapshots` với 4 trường mới (`market_history`, `sector_rotation`, `sector_health`, `methodology_version`), tương thích ngược snapshot cũ; giao diện Bức tranh thị trường 4 tab tương tác; giao diện 11 Ngành GICS theo đúng thứ tự 4 phần (KPIs tổng quan → Luân chuyển 4 góc phần tư & ma trận độ rộng/hiệu suất → Bảng sức khỏe nội bộ → Drill-down ngành chọn với Top 5 mã thanh khoản); chế độ xem kép Ma trận 127 Nhóm ngành O'Neil (COMP/BLEND vs Breadth/Median).
- **Thay đổi chính:**
  - **Chuẩn hóa Dữ liệu & RVOL Nhân quả (`analytics/market_breadth.py`, `analytics/sector_ranker.py`):** Phân biệt rõ `advances`, `declines`, `unchanged` và `missing_count`; tính `rvol_prior20` từ median 20 phiên trước của chính cổ phiếu đó; mẫu số MA20/50/200 trong ngành chỉ tính trên các mã thỏa điều kiện quan sát; bổ sung `quality_flags` và `methodology_version: v2.1`.
  - **Động cơ Phân tích Độ rộng Tham gia & Sức khỏe Ngành (`analytics/market_participation.py`):** Hàm `compute_market_breadth_history` trích xuất chuỗi thời gian EOD (loại trừ ETF khỏi breadth thành viên), tính A/D Line, AD Volume Line, Net Breadth, % MA20/50/200, lợi suất bình quân vs trung vị; hàm `compute_sector_health` tính toán sức khỏe nội bộ, phát hiện phân kỳ mega-cap, tỷ trọng thanh khoản và Top 5 mã thanh khoản cao nhất.
  - **Động cơ Luân chuyển Ngành (`analytics/sector_rotation.py`):** Hàm `compute_sector_rotation` tính tọa độ $X_t, Y_t$, phân loại 4 góc phần tư (Leading, Weakening, Lagging, Improving), lưu trữ vệt lịch sử 10 phiên liên tiếp, đánh giá bối cảnh xu hướng tuyệt đối (ETF vs MA50/MA200), tuân thủ nghiêm ngặt point-in-time lọc nến `<= as_of`.
  - **Lưu trữ & Safe Migration (`storage/database.py`, `storage/repository.py`):** Bổ sung các cột `market_history`, `sector_rotation`, `sector_health`, `methodology_version` vào bảng `snapshots` qua safe migration `ALTER TABLE`; cập nhật `save_snapshot` lưu trữ nguyên tử; hàm `_deserialize_snapshot` đảm bảo snapshot cũ không bị vỡ giao diện.
  - **Tích hợp Pipeline (`jobs/update_pipeline.py`):** Kết nối tự động gọi `compute_market_breadth_history`, `compute_sector_health`, `compute_sector_rotation` khi tạo snapshot mới.
  - **Giao diện Trực quan hóa Streamlit (`app/components/metrics_cards.py`, `app/components/sector_table.py`, `app/components/industry_heatmap.py`, `app/main.py`):**
    - `metrics_cards.py`: 4 tab chuyên sâu (A/D Line & AD Volume Line, Lịch sử Độ rộng MA, Net Breadth & AD Vol %, So sánh Lợi suất SPY vs RSP vs Median).
    - `sector_table.py`: Bố cục chuẩn mực 4 phần (1. Thẻ chỉ số tổng quan & cảnh báo phân kỳ -> 2. Biểu đồ luân chuyển 4 góc phần tư Plotly có trail 10 phiên & ma trận phụ trợ độ rộng/hiệu suất -> 3. Bảng phân tích sức khỏe nội bộ ngành -> 4. Drill-down ngành được chọn với Top 5 mã thanh khoản và nhóm ngành nhỏ).
    - `industry_heatmap.py`: Toggle chuyển đổi linh hoạt giữa Ma trận O'Neil COMP/BLEND và Ma trận Độ rộng MA50 / Lợi suất Trung vị.
- **Files / areas chạm:** `analytics/market_breadth.py`, `analytics/sector_ranker.py`, `analytics/market_participation.py`, `analytics/sector_rotation.py`, `storage/database.py`, `storage/repository.py`, `jobs/update_pipeline.py`, `app/components/metrics_cards.py`, `app/components/sector_table.py`, `app/components/industry_heatmap.py`, `app/main.py`, `tests/test_market_participation.py`, `tests/test_sector_rotation.py`, `tests/test_storage_analytics_upgrade.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest` đạt **63/63 tests pass 100%** (trong đó có 10 unit tests mới cho market participation, sector rotation, và storage migration).
  - Kiểm thử point-in-time: Dữ liệu nến tương lai bị loại trừ tuyệt đối khi tính toán với mốc `as_of`.
  - Kiểm thử phân kỳ mega-cap: Khi 1 mã lớn tăng mạnh kéo ETF tăng nhưng trung vị cổ phiếu âm, hệ thống gắn cờ phân kỳ chính xác (`is_divergent = True`).
  - Kiểm thử mẫu số độ rộng: Mã thiếu dữ liệu MA không bị gộp vào nhóm dưới MA, mẫu số phản ánh đúng số mã quan sát hợp lệ.

### [2026-09-12] Triển khai & Kiểm định Hoàn thiện Phân hệ Nhận diện Nền Giá (Đang Xây Nền / Base Building) (EXE)
- **Mode / Type / Action / Lane:** FEATURE / REVIEW / BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn phân hệ phát hiện cổ phiếu đang tích lũy đi ngang (“Đang xây nền”) trong trang Ứng viên trước khi breakout:
  1. **Động cơ Nhận diện Nền giá (`analytics/base_detector.py`):** Cửa sổ 20 phiên cố định, yêu cầu tối thiểu 40 phiên nến ngày đã đóng; tách cấu trúc nền giá (`width <= 12%`, `ER <= 0.35`, `center_shift <= 0.30`) khỏi bằng chứng tích lũy (`volume_trend`, `signed_volume_balance`); phân loại trạng thái `forming` vs `tight` (thu hẹp đồng thời TR <= 0.80 và Vol <= 0.80); đóng băng biên độ (`frozen_upper`, `frozen_lower`) từ phiên phát hiện; đánh giá breakout/breakdown nhân quả tại T theo biên T-1; tích hợp MA50, MA200, độ lệch %, Relative Strength vs SPY và hồ sơ áp lực mua bán P/V.
  2. **Quản lý Vòng đời & An toàn Dữ liệu:** Quản lý vòng đời nền (`forming`, `tight`, `breakout`, `breakdown`, `invalidated`, `closed`); xử lý fail-closed khi thiếu nến (<40) hoặc gặp nến lỗi (bảo toàn trạng thái active mà không phát tín hiệu breakdown giả); bảo vệ chống chia cho 0 khi nến phẳng (`tr_first <= 0`, `vol_first <= 0`, `sum_step_vols <= 0`).
  3. **Lưu trữ Bền vững & Idempotence (`storage/database.py`, `storage/repository.py`):** Thiết kế bảng `base_snapshots` cô lập tuyệt đối khỏi `signal_outcomes`; safe migration tự động bổ sung đầy đủ các cột kỹ thuật (`ma50`, `ma200`, `price_vs_ma50_pct`, `price_vs_ma200_pct`, `pressure_bias`); cơ chế xóa sạch bản ghi cũ theo `snapshot_id` hoặc `(as_of, symbols)` trước khi insert đảm bảo tính lũy đẳng (idempotent) 100% khi chạy lại pipeline; truy vấn `get_active_bases_by_symbol(before_date=...)` không tự tham chiếu dữ liệu phiên hiện tại.
  4. **Giao diện Theo Dõi & Xuất CSV (`app/components/base_watchlist.py`, `candidate_cards.py`, `main.py`):** Tab chuyên biệt "Đang Xây Nền" với bộ lọc trạng thái (Tất cả, Đang siết chặt, Đang hình thành, Đã bứt phá); hiển thị tách bạch ngày phát hiện ban đầu (`detected_at`) và cửa sổ 20 phiên hiện tại; checklist điều kiện; cột MA50/200 và Áp Lực P/V; xuất CSV; nút mở TradingView 1-click; cảnh báo bối cảnh thị trường.
  5. **Dòng Sự Kiện Phiên EOD Chống Trùng Lặp (`analytics/signal_events.py`, `jobs/update_pipeline.py`):** Tự động sinh sự kiện `base_forming`, `base_tight`, `base_breakout`, `base_breakdown` với `event_key` chống trùng; chỉ kích hoạt alert nền mới khi `detected_at == cur_as_of`.
  6. **Đồng bộ Luật Sàng Lọc Kỹ Thuật (`analytics/screening_rules.py`, `analytics/setup_analyzer.py`):** Chuẩn hóa mô tả `near_breakout` nêu rõ điều kiện vị trí kỹ thuật sát đỉnh 20 phiên mà không gây hiểu lầm là nền giá, tương thích ngược 100% với test suite hiện hữu.
- **Files / areas chạm:** `analytics/base_detector.py`, `storage/database.py`, `storage/repository.py`, `analytics/signal_events.py`, `analytics/screening_rules.py`, `analytics/setup_analyzer.py`, `jobs/update_pipeline.py`, `app/components/base_watchlist.py`, `app/components/candidate_cards.py`, `app/main.py`, `tests/test_base_detector.py`, `tests/test_analytics.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest` đạt **132/132 tests pass 100%** trong 16.23s (bao gồm 24 tests mới và mở rộng cho toàn bộ các ca kiểm thử biên và tính năng nền giá).
  - Python compileall: biên dịch cú pháp sạch sẽ không lỗi trên toàn bộ các package `app/`, `analytics/`, `storage/`, `config/`, `jobs/`, `tests/`.

### [2026-09-12] Khắc phục Toàn diện Domain Recheck & Nghiệm thu Sẵn sàng (R-01 đến R-06, Explore & Readiness Gate) (EXE)
- **Mode / Type / Action / Lane:** DOMAIN / ACCEPTANCE / BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Giải quyết triệt để toàn bộ 6 khiếm khuyết được nêu trong báo cáo tái kiểm định miền `docs/domain-recheck-2026-09-11.md`, hoàn thành các tính năng Explore và đưa điểm đánh giá mức độ sẵn sàng miền từ 10/16 (NOT READY) lên **15/16 (READY WITH ASSUMPTIONS cho mục đích Shortlist EOD)**:
  1. **[R-01] Xóa bỏ triệt để mạo danh SEC EDGAR cho các sự kiện kỹ thuật EOD:** Tách rành mạch `analytic_event` do Scanner tạo ra với nguồn `Market Radar Scanner (EOD OHLCV)`, `source_status = 'scanner_derived'`, link TradingView khỏi `external_company_event` (Yahoo Finance Calendar ước tính, `source_status = 'Chưa kiểm tra (Unverified)'`); sửa bug UI `today_dashboard.py` từng ép URL sang SEC EDGAR; đổi nút thành "Nguồn Scanner EOD ↗" và "Mở Chart ↗". Hạ M15 khỏi `done` công nhận trung thực là chưa có SEC ingestion pipeline.
  2. **[R-02] Chuẩn hóa hợp đồng FA & xuất xứ nguồn:** Định danh rõ nguồn `Yahoo Finance (Số liệu tổng hợp / Aggregate)`, mốc `period_end` và `retrieved_at`; loại bỏ gán ép `reported_date` hay suy diễn fiscal quarter thiếu căn cứ; duy trì cơ chế phát hiện BCTC cũ quá 180 ngày.
  3. **[R-03] Migration & Backfill hoàn chỉnh cơ sở dữ liệu SQLite:** Viết job `jobs/backfill_legacy_data.py` chạy an toàn trên bản sao DB: điền 0-null cho các trường FA metadata, chuẩn hóa toàn bộ sự kiện scanner, backfill `evidence_json` (multi-session pressure profile) cho 170 ứng viên, nạp đầy đủ 8 mốc kỳ hạn forward outcomes (1, 2, 3, 4, week-close, 5, 10, 20), khởi tạo snapshot #4 tuân thủ đầy đủ bất biến (`valid_universe <= total_universe`, 503/503 mã, 100%, 1Y: 99.2%).
  4. **[R-04] Fail-closed trạng thái chất lượng & freshness dữ liệu:** Cập nhật `compute_session_age()` bổ sung cờ `is_stale = (lag > 0)`; sửa `app/main.py` để sidebar badge và banner điều hành chuyển đỏ/vàng `Cũ ({lag} phiên)` khi dữ liệu trễ phiên mục tiêu, tuyệt đối không hiển thị màu xanh "Complete" khi dữ liệu stale; gắn nhãn `legacy_incompatible` cho snapshot #3 do vi phạm bất biến `valid > total`.
  5. **[R-05] Ngôn từ bằng chứng khách quan cho áp lực đa phiên & nến nhật:** Loại bỏ toàn bộ từ vựng gán ghép ý chí chủ quan ("lực cầu hấp thụ tốt", "phe bán áp đảo", "dòng tiền gom hàng"), thay bằng sự thật quan sát được ("đóng gần đỉnh/đáy biên độ với RVOL X", "bằng chứng thuận cho phía mua/bán").
  6. **[R-06] Kiểm soát rủi ro vắt qua cuối tuần (`crosses_weekend`) & Kiểm toán độ tin cậy mẫu:** Bổ sung cột `crosses_weekend` vào bảng `signal_outcomes` và repository; tự động tính toán phát hiện các lệnh giữ vắt qua 2 ngày nghỉ cuối tuần (crosses_weekend = 1) vs lệnh hoàn tất trong tuần (crosses_weekend = 0); bổ sung bộ lọc "Biên cuối tuần" trong `signal_performance.py`; đặt ngưỡng kiểm định mẫu tối thiểu (`MIN_SAMPLE_THRESHOLD = 5`) hiển thị cảnh báo "⚠️ Thiếu mẫu" khi chưa đủ độ tin cậy thống kê.
  7. **[Explore] So sánh trực diện 2–5 ứng viên & Lọc số phiên còn lại trong tuần:** Xây dựng `render_candidates_comparison()` cho phép trader chọn 2 đến 5 mã để so sánh song song thẻ bento (setup, giá, trigger, invalidation, stop risk %, hiệu suất 1D/1W/1M, ATR%, điểm score, áp lực đa phiên, tăng trưởng doanh thu/EPS YoY, link TradingView); bổ sung hàm `get_remaining_trading_sessions_in_week()` tính chính xác số phiên còn lại trong tuần trừ ngày nghỉ lễ NYSE; hiển thị banner cảnh báo khi tuần còn <= 1 phiên và bộ lọc ẩn các cơ hội swing đa phiên khi không đủ số ngày trong tuần.
- **Files / areas chạm:** `analytics/market_calendar.py`, `analytics/signal_events.py`, `analytics/signal_outcomes.py`, `storage/database.py`, `storage/repository.py`, `jobs/backfill_legacy_data.py`, `app/main.py`, `app/components/today_dashboard.py`, `app/components/signal_performance.py`, `app/components/candidate_cards.py`, `tests/test_domain_recheck.py`, `tests/test_swing_features.py`, `docs/domain-recheck-2026-09-11.md`, `README.md`.
- **Verify:**
  - `pytest -v` đạt **99/99 tests pass 100%** trong 11.67s (bao gồm 13 acceptance & regression tests mới trong `test_domain_recheck.py`).
  - Chạy thực nghiệm migration rehearsal `jobs/backfill_legacy_data.py`: backfill 1,360 records forward outcomes, chuẩn hóa 170 candidate pressure profiles và 167 FA records.
  - Tái thẩm định Domain Readiness: Nâng điểm từ **10/16 (NOT READY)** lên **15/16 (READY WITH ASSUMPTIONS)**.

### [2026-09-11] Rà soát Độc lập & Khắc phục Khiếm khuyết Miền Tài chính (Review & Bugfix / Boost) (EXE)
- **Mode / Type / Action / Lane:** REVIEW / BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Rà soát phản biện độc lập toàn diện các thay đổi miền tài chính (D-01 -> D-06); phát hiện và khắc phục triệt để 8 lỗi logic, thiếu sót dữ liệu và bất đối xứng kỹ thuật:
  1. **Thiếu lưu vết Entry Date & Entry Price:** Cột `entry_date`, `entry_price` và `spy_entry_price` trong bảng `signal_records` luôn bị để NULL sau khi tạo streak ban đầu, khiến bảng hiệu quả tín hiệu trên UI hiển thị "Chờ phiên sau" và giá None cho các tín hiệu đã hoàn tất -> triển khai `update_signal_entry_info()` tại `storage/repository.py`, cập nhật tự động trong `jobs/update_signal_outcomes.py`, trả về đầy đủ `entry_date`, `entry_price`, `spy_entry_price` trong `evaluate_signal_outcomes()`.
  2. **Lỗi Kiểu Dữ liệu Serialization (`setup_analyzer.py:549`):** Trả về `"symbol": symbol` thay vì `sym_str`, gây lỗi `TypeError` khi `symbol` là DataFrame.
  3. **Cụt Lịch sử Median Volume 20 phiên (`setup_analyzer.py:399-407`):** Cắt `tail(25)` trước khi tính rolling 20 median volume làm mất dữ liệu của các phiên trước -> chuyển sang tính trên toàn bộ `df` trước khi lấy `tail(5)`.
  4. **Bất đối xứng Cảnh báo Mở rộng Giá MA20 (`setup_analyzer.py:250`):** Chỉ kiểm tra quá mua cho Long (`dist_ma20_atr > 1.5`), bỏ sót Short -> bổ sung đối xứng kiểm tra Short quá bán (`dist_ma20_atr < -1.5`) với cảnh báo rủi ro short squeeze / hồi kỹ thuật.
  5. **Modal Bị Kẹt 1 Phiên Áp lực (`setup_detail.py:226`):** Candidate screening mang sẵn placeholder 1 phiên khiến `if not pressure_data` trả về False và không bao giờ tính profile 5 phiên thực sự từ `full_bars` -> sửa thành `if (not pressure_data or pressure_data.get("n_sessions", 0) < 5) and not full_bars.empty:`.
  6. **Lỗi Parse Ngày BCTC Chuỗi Ký tự (`yfinance_provider.py:143`):** Cung cấp hàm `_parse_date_or_ts()` hỗ trợ linh hoạt Unix integer timestamp, chuỗi ISO, chuỗi US date và Pandas Timestamp.
  7. **Thiếu Phát hiện BCTC Cũ Lạc Hậu (`company_fa.py:125`):** Phát hiện BCTC cũ > 180 ngày so với `ref_date`, gắn cờ `is_stale=True`, nâng `warning_level="medium"` và gắn cảnh báo kiểm chứng hồ sơ mới nhất.
  8. **Củng cố Kết thúc Tuần & Đếm Mẫu (`signal_outcomes.py:252`):** Bổ sung điều kiện `market_in_later_week` chống kẹt pending khi dữ liệu thị trường đã bước sang tuần mới; chuẩn hóa số mẫu `len(g_rets)` và nhãn "Long (Mua)" / "Short (Bán khống)".
- **Files / areas chạm:** `analytics/signal_outcomes.py`, `storage/repository.py`, `jobs/update_signal_outcomes.py`, `analytics/setup_analyzer.py`, `app/components/setup_detail.py`, `providers/yfinance_provider.py`, `analytics/company_fa.py`, `tests/test_swing_features.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest -v` đạt **86/86 tests pass 100%** (trong đó có 5 unit & integration tests hồi quy mới).
  - Kiểm thử bền vững việc ghi đè entry price, kiểm thử stale BCTC > 180 ngày, kiểm thử parse đa dạng kiểu ngày và kiểm thử cảnh báo overextended short.

### [2026-09-11] Hoàn thiện Toàn diện 6 Khoảng trống Miền Tài chính (Domain Gap Closures D-01 -> D-06 / Boost) (EXE)
- **Mode / Type / Action / Lane:** FEATURE / DOMAIN / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn 6 khoảng trống miền tài chính theo kế hoạch review chuyên sâu tại `docs/domain-needs-review-2026-09-11.md`: (D-01) Chuẩn hóa xuất xứ và mốc đối chiếu BCTC (Fiscal Period MRQ/FY, Quarterly YoY, đồng tiền USD, nguồn cấp Yahoo Finance proxy, nút 1-click mở trực tiếp hồ sơ SEC EDGAR); (D-02) Mở rộng dòng sự kiện doanh nghiệp ngoài BCTC kèm link nguồn IR/SEC, thời điểm công bố/thu thập và cờ phân loại nguồn (`confirmed` vs `unverified`) kèm banner cảnh báo; (D-03) Xây dựng hồ sơ áp lực mua/bán đa phiên (1/3/5 phiên) với 3 khối bằng chứng cấu trúc (ủng hộ, mâu thuẫn, trung tính), loại bỏ triệt để từ vựng gây hiểu lầm "net inflow / tổ chức gom hàng", thay thế bằng GTGD ước tính và độ rộng thị trường; (D-04) Mở rộng đo lường chất lượng scanner sang các kỳ hạn giữ ngắn trong tuần (1, 2, 3, 4 phiên và Chốt cuối tuần 99), tự động loại trừ/gắn cờ ca vào phiên cuối tuần không còn window trong tuần (`no_window_in_week`), phân rã thống kê theo Thứ trong tuần (Thứ Hai -> Thứ Sáu) và Chiều giao dịch (Long vs Short), kèm khuyến cáo phân biệt Gross Return vs Real Trade P&L; (D-05) Đồng hồ thị trường thời gian thực (New York ET và Việt Nam ICT), nhận diện trạng thái NYSE chuẩn xác (Pre-market, Regular, After-hours, Closed, Holiday, Weekend) và hàm tính độ trễ phiên (`compute_session_age`); (D-06) Tuyên bố minh bạch phạm vi vũ trụ 503 cổ phiếu S&P 500 (Large-Cap) trên thanh bên và banner điều hành, làm rõ lý do không quét toàn bộ ~8.000 mã Mỹ hay OTC/penny stocks; di chuyển an toàn cơ sở dữ liệu SQLite cho 3 bảng `fundamentals`, `signal_events`, `signal_outcomes` và bổ sung unit tests nâng tổng số lên 81/81 tests pass 100%.
- **Thay đổi chính:**
  - **D-01 (Bối cảnh FA & Xuất xứ dữ liệu):**
    - `storage/database.py` & `storage/repository.py`: Safe migration thêm các cột `fiscal_period`, `period_type`, `currency`, `reported_date`, `source`, `data_status`, `sec_filing_url` vào bảng `fundamentals`.
    - `providers/yfinance_provider.py`: Trích xuất kỳ BCTC (`mostRecentQuarter`, `lastFiscalYearEnd`), tiền tệ và link tra cứu SEC EDGAR.
    - `analytics/company_fa.py`: `evaluate_fa_flags()` gắn nhãn kỳ báo cáo, cơ sở đối chiếu YoY MRQ, xuất xứ nguồn và disclaimer BCTC.
    - `app/components/candidate_cards.py` & `setup_detail.py`: Hiển thị badge kỳ BCTC, xuất xứ và nút link trực tiếp SEC EDGAR.
  - **D-02 (Sự kiện Doanh nghiệp & Nguồn Kiểm chứng):**
    - `storage/database.py` & `storage/repository.py`: Safe migration thêm `source_url`, `source_name`, `published_at`, `received_at`, `source_status` vào bảng `signal_events`.
    - `analytics/signal_events.py`: Tự động điền metadata nguồn, cờ `confirmed` hoặc `Chưa kiểm tra (Unverified)`.
    - `app/components/today_dashboard.py`: Hiển thị badge nguồn, timestamp công bố/thu thập, nút link tài liệu gốc và banner cảnh báo nguồn chưa kiểm chứng.
  - **D-03 (Áp lực Mua/Bán Đa phiên & Thanh khoản Chuẩn xác):**
    - `analytics/market_participation.py`, `app/components/sector_table.py`, `metrics_cards.py`: Loại bỏ hoàn toàn cụm từ "dòng tiền ròng" / "tập trung dòng tiền", thay bằng "Giá trị giao dịch (GTGD) ước tính" và "Mức tập trung giao dịch: Top 5 mã chiếm X% tổng GTGD ước tính của ngành".
    - `analytics/setup_analyzer.py`: Xây dựng engine `analyze_multi_session_pressure()` đo lường vị trí đóng cửa trong phiên (close position in range), khối lượng tương đối (RVOL), trích xuất 3 khối bằng chứng cấu trúc (`supporting_evidence`, `contradicting_evidence`, `neutral_gaps`), chỉ định `pressure_bias` khách quan kèm ghi chú phương pháp luận.
    - `app/components/setup_detail.py`: Hiển thị bảng dữ liệu 5 phiên, 3 khối bằng chứng và lưu ý phương pháp luận không ngộ nhận order book.
  - **D-04 (Outcomes Swing Trong Tuần & Phân Nhóm Thống Kê):**
    - `storage/database.py` & `storage/repository.py`: Safe migration thêm `entry_day_of_week` và `horizon_label` vào bảng `signal_outcomes`.
    - `analytics/signal_outcomes.py`: Mở rộng `evaluate_signal_outcomes()` hỗ trợ các kỳ hạn 1, 2, 3, 4 phiên và Chốt cuối tuần (99 / week-close); phát hiện tín hiệu vào phiên cuối tuần (Thứ Sáu hoặc Thứ Năm trước kỳ nghỉ) và gắn cờ `no_window_in_week`; `compute_quality_summary()` bổ sung bảng thống kê theo Thứ vào lệnh (`weekday_breakdown`) và theo Chiều giao dịch (`side_breakdown`).
    - `app/components/signal_performance.py`: Thêm bộ chọn kỳ hạn (1-4 phiên swing, Chốt cuối tuần, 5/10/20 phiên macro), bảng phân tích theo Thứ, bảng Long vs Short và banner cảnh báo Gross Edge vs Real P&L.
    - `jobs/update_signal_outcomes.py`: Cập nhật job đánh giá đầy đủ toàn bộ các mốc kỳ hạn.
  - **D-05 (Đồng hồ Thị trường & Độ tươi Snapshot):**
    - `analytics/market_calendar.py`: Xây dựng `get_market_status_now()` cung cấp đồng hồ New York (ET) & Việt Nam (ICT), trạng thái phiên NYSE; xây dựng `compute_session_age()` tính toán độ trễ phiên (0 = mới nhất, >0 = dữ liệu lịch sử chậm X phiên).
    - `app/main.py`: Render Banner Điều Hành (Executive Market Clock, Freshness & Scope Banner) ở vị trí trang trọng đầu ứng dụng.
  - **D-06 (Minh bạch Phạm vi Vũ trụ S&P 500):**
    - `app/main.py` & sidebar: Công bố rõ ràng phạm vi vũ trụ là 503 cổ phiếu thành phần rổ S&P 500 (Large Cap), ghi chú lý do không bao gồm penny/OTC hay toàn bộ ~8.000 mã Mỹ; minh bạch bản chất dữ liệu là giá đóng cửa EOD đã điều chỉnh.
- **Files / areas chạm:** `analytics/company_fa.py`, `analytics/market_breadth.py`, `analytics/market_calendar.py`, `analytics/market_participation.py`, `analytics/screening_rules.py`, `analytics/sector_ranker.py`, `analytics/setup_analyzer.py`, `analytics/signal_events.py`, `analytics/signal_outcomes.py`, `app/components/candidate_cards.py`, `app/components/metrics_cards.py`, `app/components/sector_table.py`, `app/components/setup_detail.py`, `app/components/signal_performance.py`, `app/components/today_dashboard.py`, `app/main.py`, `config/settings.py`, `jobs/update_pipeline.py`, `jobs/update_signal_outcomes.py`, `providers/yfinance_provider.py`, `storage/database.py`, `storage/repository.py`, `tests/test_swing_features.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest -v` đạt **81/81 tests pass 100%** trong 8.33s (bổ sung 3 unit tests mới cho multi-session pressure, intra-week outcomes/week close, và market clock/session age).
  - Khởi chạy Dashboard: Toàn bộ banner đồng hồ thị trường, độ tươi snapshot, modal chi tiết setup và phân tích hiệu quả tín hiệu hoạt động chuẩn xác, không văng lỗi.

### [2026-09-10] Tái Cấu Trúc UX/UI: Kiến Trúc 3 Trụ Cột, Modal Setup 3 Tab & Xuất CSV Ngữ Cảnh (EXE)
- **Mode / Type / Action / Lane:** REFACTOR / ENHANCEMENT / EXECUTE / n/a
- **Tóm tắt:** Tái quy hoạch toàn diện giao diện từ thanh 7 tab phẳng dàn trải thành kiến trúc 3 Trụ Cột (3-Pillar Workspaces) điều hướng 2 cấp bám sát luồng phân tích Top-Down của trader; cải tiến modal chi tiết setup (`setup_detail.py`) thành 3 tab nội bộ (`Kỹ Thuật & Mức Giá`, `Nến Nhật & FA`, `Checklist & Xuất CSV`) giải quyết triệt để tình trạng cuộn chuột dài 1500px; bổ sung nút tải CSV ứng viên ngữ cảnh ngay trên thanh công cụ; tách bạch hiển thị độc lập giữa 11 Ngành GICS và Ma trận 127 Nhóm ngành O'Neil; ổn định bố cục nút hành động trên thẻ sự kiện Hôm nay; và bảo toàn 100% logic kinh doanh và 53/53 automated tests.
- **Thay đổi chính:**
  - **Kiến trúc Điều hướng 2 cấp (`app/main.py`):** Cấp 1 gồm 3 Trụ Cột: `🎯 Hôm Nay & Ứng Viên` (kèm badge sự kiện mới), `🌐 Bản Đồ Thị Trường & Ngành` và `📊 Đo Lường & Kiểm Toán`. Cấp 2 hiển thị các góc nhìn tương ứng theo từng trụ cột, chỉ render view đang chọn để đảm bảo tốc độ và chống phình to DOM.
  - **Tái cấu trúc Modal Chi tiết Setup (`app/components/setup_detail.py`):** Gom pre-fetch dữ liệu nến và FA một lần duy nhất; phân rã nội dung popup thành 3 tab con (`Kỹ Thuật & Mức Giá` [Chart PIT + Levels table + CSV], `Nến Nhật & Bối Cảnh FA` [Chỉ số Lớp 1/2 + Ngưỡng nhận diện + FA/Earnings], `Checklist & Điều Kiện` [Pass/Fail/NA + Short caveat + TradingView link]), loại bỏ hoàn toàn tình trạng phải cuộn chuột dài trong dialog.
  - **Bổ sung Xuất CSV Ngữ Cảnh (`app/components/candidate_cards.py`):** Đưa nút tải CSV danh sách ứng viên (`Xuất CSV Ứng viên 📥`) lên thanh điều khiển trên cùng cạnh ô tìm kiếm và checkbox Leader, giúp người dùng tải dữ liệu trực tiếp mà không cần tìm xuống chân sidebar.
  - **Tách Góc nhìn Ngành Linh hoạt (`app/components/sector_table.py`):** Trích xuất hàm `render_gics_sectors()` độc lập và nâng cấp `render_sector_section()` hỗ trợ tham số `view_mode` (`macro` hoặc `heatmap`), cho phép gọi trực tiếp từng phân hệ từ thanh điều hướng chính.
  - **Ổn định Bố cục Nút Sự Kiện (`app/components/today_dashboard.py`):** Bổ sung trạng thái disabled cho nút "Đã đọc" khi sự kiện đã được đọc, đảm bảo chiều cao 3 nút hành động (`TradingView`, `Đã đọc`, `Chi tiết`) đồng nhất trên mọi hàng.
- **Files / areas chạm:** `app/main.py`, `app/components/setup_detail.py`, `app/components/candidate_cards.py`, `app/components/sector_table.py`, `app/components/today_dashboard.py`, `README.md`.
- **Verify:**
  - `pytest -v` đạt **53/53 tests pass 100%**.
  - Kiểm tra giao diện Streamlit: Chuyển đổi mượt mà giữa 3 trụ cột và 8 góc nhìn; modal setup hiển thị 3 tab gọn gàng không cuộn dài; nút xuất CSV hoạt động chính xác.

### [2026-09-09] Khắc phục Lỗi get_unread_event_count & Đồng bộ Đếm Sự kiện Theo Phiên (Bugfix) `(EXE)`
- **Mode / Type / Action / Lane:** BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Khắc phục triệt để lỗi `AttributeError: 'MarketRadarRepository' object has no attribute 'get_unread_event_count'` tại `app/main.py:275`; loại bỏ hoàn toàn antipattern `importlib.reload()` và các lớp bọc `hasattr()` che giấu lỗi; chuẩn hóa phương thức `get_unread_event_count()` hỗ trợ lọc theo phiên giao dịch (`session_date: Optional[str] = None`); sửa logic "Đánh dấu tất cả đã đọc" trong `today_dashboard.py` tương thích với cơ chế fallback; bọc bảo vệ an toàn các thao tác ghi SQLite; và bổ sung 2 unit tests kiểm thử hồi quy nâng tổng số tests lên 53/53 passed 100%.
- **Thay đổi chính:**
  - **Chuẩn hóa Repository Contract (`storage/repository.py`):** Bổ sung tham số `session_date: Optional[str] = None` vào `get_unread_event_count(session_date=...)` lọc `WHERE is_read = 0 AND session_date = ?` nếu có hoặc đếm toàn bộ nếu không truyền; bọc `try...except Exception: pass` cho `mark_event_read` và `mark_all_events_read` chống lỗi khóa SQLite.
  - **Làm sạch Entry Point (`app/main.py`):** Xóa bỏ module reload và defensive checking `hasattr()`; đồng bộ số lượng sự kiện chưa đọc trên nhãn tab `00 Hôm nay` theo phiên giao dịch đang chọn của snapshot.
  - **Xử lý Đánh dấu đã đọc (`app/components/today_dashboard.py`):** Cập nhật nút "Đánh dấu tất cả đã đọc" xác định đúng ngày phiên của danh sách sự kiện đang hiển thị (kể cả khi đang nạp sự kiện dự phòng).
  - **Kiểm thử Hồi quy (`tests/test_storage.py`):** Bổ sung `test_get_unread_event_count` và `test_today_dashboard_event_mark_read_and_fallback`.
- **Files / areas chạm:** `storage/repository.py`, `app/main.py`, `app/components/today_dashboard.py`, `tests/test_storage.py`, `README.md`.
- **Verify:**
  - `pytest -v` đạt **53/53 tests pass 100%**.
  - Kiểm tra `curl.exe -sI http://localhost:8501` trả về `HTTP/1.1 200 OK`.

### [2026-09-08] Rà soát Độc lập & Khắc phục Toàn diện (Independent Review & Bugfix) `(EXE)`
- **Mode / Type / Action / Lane:** REVIEW / BUGFIX / REFACTOR / EXECUTE / n/a
- **Tóm tắt:** Rà soát phản biện độc lập toàn bộ các thay đổi của vòng trước; phát hiện và khắc phục triệt để lỗi chí mạng `NameError: name 'repo' is not defined` khi hiển thị thẻ ứng viên thiếu FA; loại trừ rò rỉ dữ liệu tương lai (lookahead leak) khi đánh giá FA trên snapshot cũ; sửa lỗi tính MA200 bị cụt trên biểu đồ nến do slice `tail(90)` trước khi rolling; bảo toàn mẫu nến kích hoạt ban đầu (inception candle pattern) trong chuỗi tín hiệu; hiển thị trực quan dải chỉ số Lớp 1 (Đặc điểm hình học nến) song song với Lớp 2 (Thông dịch phản ứng setup); thắt chặt ngưỡng nhận diện nến búa và sao băng với chặn râu đối diện; bổ sung bộ chọn xem chi tiết setup ngay trong chế độ Bảng Rút Gọn; và bổ sung 5 unit tests hồi quy chuyên sâu.
- **Thay đổi chính:**
  - **Sửa lỗi chí mạng NameError (`app/components/candidate_cards.py`):** Bổ sung tham số `as_of: str = ""` và `repo: Optional[Any] = None` vào `render_candidate_card()`; truyền đầy đủ `repo=repo` từ vòng lặp nhóm ứng viên; kiểm tra an toàn `repo is not None` trước khi fallback tra cứu database; bổ sung dropdown chọn xem chi tiết setup ngay trong chế độ "Bảng Rút Gọn".
  - **Triệt tiêu rò rỉ dữ liệu tương lai (`app/components/candidate_cards.py`, `app/components/setup_detail.py`):** Truyền tham số `ref_date=as_of_clean` vào `evaluate_fa_flags()` khi fallback tra cứu, đảm bảo số ngày đến kỳ BCTC (`days_to_earnings`) luôn được tính chuẩn xác theo mốc point-in-time của snapshot, không bị lấy nhầm theo ngày hiện tại (`date.today()`).
  - **Khắc phục đường MA200 trên biểu đồ (`app/components/setup_detail.py`):** Gom việc truy vấn dữ liệu nến thành 1 lần duy nhất; tính toán toàn bộ các đường trung bình động MA20, MA50, MA200 trên toàn bộ lịch sử nến trước khi cắt lấy 90 nến cuối (`tail(90)`) để vẽ biểu đồ, loại bỏ hoàn toàn tình trạng MA200 bị tính cụt thành đường trung bình 50-90 phiên.
  - **Bảo toàn Mẫu nến Khởi phát trong Chuỗi Tín hiệu (`analytics/signal_outcomes.py`):** Sửa logic `process_signal_streaks()` ưu tiên giữ lại `existing.get("candle_pattern")` khi chuỗi tín hiệu kéo dài sang phiên thứ 2, thứ 3; ngăn chặn việc mẫu nến ngày sau (Inside bar / Doji) ghi đè làm mất mẫu nến kích hoạt breakout/pullback ban đầu của tín hiệu.
  - **Bộc lộ Rõ nét Kiến trúc Nến 2 Lớp (`app/components/setup_detail.py`, `analytics/setup_analyzer.py`):** Bổ sung dải 4 ô chỉ số định lượng Lớp 1 (Chiều & % Thân, Tỷ lệ Râu trên / Râu dưới, Vị trí đóng cửa trong phiên, Tỷ lệ Biên độ / ATR14) ngay phía trên phần thông dịch Lớp 2 (Mẫu hình & Bối cảnh phản ứng setup); bổ sung ngưỡng chặn râu đối diện cho Hammer (`upper_shadow <= 25%`) và Shooting Star (`lower_shadow <= 25%`) trong `CANDLESTICK_THRESHOLDS`.
  - **Bổ sung Bộ Kiểm thử Đơn vị Chuyên sâu (`tests/test_swing_features.py`):** Thêm 5 unit tests kiểm thử hồi quy: (1) Render thẻ ứng viên khi thiếu FA với `repo=None` và `repo=MockRepo` không văng lỗi; (2) Đánh giá point-in-time FA không lookahead; (3) Bảo toàn mẫu nến inception qua chuỗi nhiều phiên; (4) Từ chối nhận diện nến búa khi râu trên dài vượt ngưỡng; (5) Xử lý an toàn nến phẳng biên độ bằng 0 (flat halt bar).
- **Files / areas chạm:** `app/components/candidate_cards.py`, `app/components/setup_detail.py`, `analytics/setup_analyzer.py`, `analytics/signal_outcomes.py`, `tests/test_swing_features.py`, `README.md`.
- **Verify:**
  - Chạy toàn bộ test suite: `pytest -v` đạt **51/51 tests pass 100%** (trong đó có 5 regression tests mới).
  - Kiểm thử trực tiếp bằng Python script: `render_candidate_card` trên các ứng viên của Snapshot #1 và #2 không còn văng `NameError`.
  - Kiểm tra giao diện và tính toán moving average: `ma200` chuẩn xác, dải chỉ số Lớp 1 hiển thị đầy đủ.

### [2026-09-08] Bổ sung Nhận diện Nến Nhật (Candlestick) & Khắc phục Dữ liệu FA `(EXE)`
- **Mode / Type / Action / Lane:** FEATURE / BUGFIX / EXECUTE / n/a
- **Tóm tắt:** Giải quyết triệt để vấn đề dữ liệu FA hiển thị placeholder sơ sài bằng cơ chế tra cứu dự phòng (fallback lookup) từ kho dữ liệu local SQLite và backfill snapshot; đồng thời tích hợp toàn diện 2 tầng nhận diện nến nhật ngày gần nhất đã đóng (Daily Candlestick Analysis): hình thái hình học thuần túy (Doji, Marubozu, Hammer, Shooting Star, Engulfing, Inside/Outside Bar) và thông dịch định tính theo ngữ cảnh setup 3 dòng (Nến gần nhất, Bối cảnh, Trạng thái phản ứng), công bố rõ ràng ngưỡng nhận diện, tích hợp vào checklist mà không can thiệp méo mó điểm ranking, và bổ sung công cụ khảo sát lợi thế mẫu nến (Candlestick Edge Audit) trong màn hình Hiệu quả tín hiệu.
- **Thay đổi chính:**
  - **Khắc phục hiển thị dữ liệu FA (`app/components/candidate_cards.py`, `app/components/setup_detail.py`):** Xóa bỏ dòng chữ placeholder vô nghĩa; bổ sung cơ chế fallback tra cứu trực tiếp từ bảng `fundamentals` trong SQLite repository khi snapshot thiếu dữ liệu FA; hiển thị đầy đủ tăng trưởng Doanh thu, EPS, Biên LN ròng, số ngày đến kỳ BCTC và các nhãn cảnh báo đặc thù.
  - **Động cơ Nhận diện & Thông dịch Nến Nhật (`analytics/setup_analyzer.py`, `analytics/market_breadth.py`):** Bổ sung lưu trữ nến trước (`prev_open`, `prev_high`, `prev_low`, `prev_close`); xây dựng hàm `analyze_candlestick()` định lượng hình học 7 mẫu nến kinh điển và nhãn "Không rõ mẫu hình" khi dao động chuẩn; hàm `interpret_candlestick_in_setup()` thông dịch vị trí xuất hiện (VD: Hammer tại hỗ trợ MA20 xác nhận phản ứng tốt vs sau nhịp tăng xa MA20 > 1.5 ATR tiềm ẩn rủi ro mua đuổi); công bố công khai bảng ngưỡng nhận diện định lượng (`CANDLESTICK_THRESHOLDS`).
  - **Tích hợp Checklist & Lan truyền Dữ liệu (`analytics/screening_rules.py`, `analytics/setup_analyzer.py`):** Bổ sung tiêu chí số 6 "Nến gần nhất & Phản ứng giá" vào checklist của từng ứng viên; chuyển giao `candle_pattern` và `candlestick_analysis` vào snapshot mà không can thiệp làm sai lệch điểm số định lượng của scanner.
  - **Cơ sở Dữ liệu & Safe Migration (`storage/database.py`, `storage/repository.py`):** Bổ sung cột `candle_pattern TEXT DEFAULT 'Không rõ mẫu hình'` vào hai bảng `candidate_snapshots` và `signal_records`; cập nhật truy vấn `save_snapshot`, `get_candidates_by_snapshot`, `upsert_signal_records` và `get_signal_outcomes`. Chạy backfill cập nhật an toàn dữ liệu FA và nến nhật cho snapshot #3 hiện hữu.
  - **Khảo sát Lợi thế Nến trong Setup (`analytics/signal_outcomes.py`, `app/components/signal_performance.py`):** Mở rộng engine tính toán outcomes phân rã theo mẫu nến (`candle_breakdown` và `setup_candle_breakdown`); thêm bảng "Khảo Sát Mẫu Nến Trong Setup (Candlestick Edge Audit)" cho phép lọc theo loại setup và so sánh xác suất thắng, tỷ suất sinh lời, MFE/MAE giữa các mẫu nến.
  - **Giao diện Chi tiết Setup (`app/components/setup_detail.py`):** Khối hiển thị nhận diện nến 3 dòng trực quan với nhãn trạng thái phản ứng (xanh/vàng/đỏ), ngày nến EOD chốt phiên và expander công bố quy tắc/ngưỡng nhận diện định lượng bằng chuỗi raw markdown chuẩn xác.
- **Files / areas chạm:** `analytics/setup_analyzer.py`, `analytics/market_breadth.py`, `analytics/screening_rules.py`, `storage/database.py`, `storage/repository.py`, `analytics/signal_outcomes.py`, `app/components/setup_detail.py`, `app/components/candidate_cards.py`, `app/components/signal_performance.py`, `tests/test_swing_features.py`, `README.md`.
- **Verify:**
  - Bộ kiểm thử tự động toàn diện: `pytest tests/ -v` đạt **46/46 tests pass 100%** (trong đó có 4 tests mới cho mẫu nến, thông dịch ngữ cảnh, checklist và outcomes breakdown).
  - Khắc phục triệt để cú pháp escape warning trong Streamlit expander markdown.
  - Xác nhận cơ sở dữ liệu `market_radar.db` được backfill chuẩn xác 170 ứng viên với FA flags, candlestick analysis và signal records.

### [2026-09-08] Hoàn thiện Workstation Swing Trading: Chi tiết Setup, Trang Hôm nay & Đo lường Hiệu quả Tín hiệu (Mục 2, 6, 7) `(EXE)`
- **Mode / Type / Action / Lane:** FEATURE / ENHANCEMENT / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn bộ ba tính năng trọng tâm theo kế hoạch đã chốt (Mục 2, 6, 7): (1) Chi tiết setup & playbook với bối cảnh đa khung (ngày/tuần, đánh dấu tuần chưa đóng), các mức kỹ thuật tham chiếu khách quan (trigger, invalidation, support, resistance) kèm căn cứ, biến động ATR14/ATR%, thanh khoản 20 phiên/relative volume, checklist điều kiện đạt/chưa đạt/thiếu dữ liệu, biểu đồ gọn point-in-time không rò rỉ dữ liệu tương lai và xuất CSV cho Excel; (2) Trang "Hôm nay" đưa lên đầu ứng dụng 4 nhóm sự kiện (cơ hội mới, thay đổi setup, sự kiện BCTC sắp tới, biến động thị trường/ngành) với định danh sự kiện chống trùng lặp tuyệt đối, so sánh liên phiên, loại trừ ca mất mã do thiếu dữ liệu; (3) Màn hình "Hiệu quả tín hiệu" đo lường độc lập chất lượng bộ lọc scanner (forward returns 5/10/20 phiên lấy mốc giá Open phiên kế tiếp, chênh lệch vs SPY, MFE/MAE theo % và ATR, kiểm định tính đơn điệu của score, theo dõi setup liên tiếp theo đợt); cùng bộ lịch thị trường NYSE/NASDAQ chuẩn hóa ngày nghỉ lễ và phiên đóng sớm 13:00 ET.
- **Thay đổi chính:**
  - **Nền tảng Dữ liệu & Lịch Giao dịch (`analytics/market_calendar.py`):** Xây dựng module lịch thị trường chứng khoán Mỹ xử lý chuẩn xác toàn bộ ngày lễ NYSE/NASDAQ (New Year, MLK, Presidents' Day, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas) và các phiên đóng cửa sớm 13:00 ET (Black Friday, Christmas Eve, July 3). Hỗ trợ xác định phiên EOD và trạng thái kết thúc tuần giao dịch (`is_end_of_trading_week`).
  - **Cơ sở dữ liệu & Safe Migration (`storage/database.py`, `storage/repository.py`):** Backup an toàn database `market_radar.db.bak`. Bổ sung bảng `signal_events` (có `event_key` chống trùng lặp), `signal_records` (theo dõi chuỗi tín hiệu/streak), `signal_outcomes` (lưu trữ kết quả 5/10/20 phiên forward). Mở rộng bảng `candidate_snapshots` với 19 cột kỹ thuật mới (`setup_type`, `trigger_price`, `trigger_condition`, `invalidation_price`, `invalidation_condition`, `support_level`, `resistance_level`, `atr14`, `atr_pct`, `dist_trigger_pct`, `dist_trigger_atr`, `dist_ma20_pct`, `dist_ma20_atr`, `avg_dollar_vol20`, `rel_volume`, `weekly_context`, `checklist`, `evidence_json`, `signal_key`). Nâng cấp hàm `get_snapshot_diff` phân biệt theo cặp `(symbol, setup_type)` và so sánh theo các phiên giao dịch thực sự.
  - **Chỉ số Kỹ thuật Bổ sung & Bối cảnh Đa khung (`analytics/market_breadth.py`):** Bổ sung tính toán True Range & Wilder ATR 14 phiên, ATR%, giá trị giao dịch trung bình 20 phiên (`avg_dollar_vol20`), khối lượng tương đối (`rel_volume`), resample dữ liệu nến tuần W-FRI để trích xuất xu hướng tuần (Weekly trend, Weekly MA10/MA30) và gắn nhãn tuần chưa đóng (`is_week_closed`).
  - **Động cơ Phân tích Setup (`analytics/setup_analyzer.py`, `analytics/screening_rules.py`):** Tách logic mô tả setup sang module mới; phân loại chi tiết các subtype (breakout, near_breakout, pullback_ma20, pullback_ma50, breakdown, near_breakdown, pullback_ma20_res, reversal_reclaim, reversal_drop); xác định mức kích hoạt, vô hiệu hóa, hỗ trợ/kháng cự kèm căn cứ xác định; xây dựng checklist cấu trúc định lượng (Pass/Fail/N/A); đánh giá rủi ro mở rộng (Extension > 1.5 ATR).
  - **Giao diện Chi tiết Setup (`app/components/setup_detail.py`):** Màn hình drill-down chuyên sâu: thẻ chỉ số biến động/thanh khoản/khung tuần, biểu đồ nến & volume compact point-in-time vẽ kèm đường MA và các mức trigger/invalidation/support/resistance, bảng thông số kỹ thuật chuẩn hóa để xuất CSV copy sang Excel, checklist kiểm định điều kiện và link TradingView 1-click. Cập nhật `candidate_cards.py` dùng cột số chuẩn xác định dạng giúp sort đúng theo giá trị.
  - **Phát hiện Sự kiện & Trang Hôm nay (`analytics/signal_events.py`, `app/components/today_dashboard.py`):** Sinh dòng sự kiện phiên EOD gồm 4 nhóm: Cơ hội mới, Thay đổi setup, Sự kiện BCTC, Biến động thị trường/ngành. Lưu trữ SQLite với khóa chống trùng `event_key`; có bộ lọc trạng thái đọc và nút "Đánh dấu tất cả đã đọc".
  - **Đo lường Chất lượng Scanner (`analytics/signal_outcomes.py`, `jobs/update_signal_outcomes.py`, `app/components/signal_performance.py`):** Động cơ theo dõi chuỗi tín hiệu (signal streaks) không nhân đôi khi xuất hiện nhiều phiên; lấy giá Open phiên kế tiếp làm mốc vào lệnh chuẩn; tính toán forward return sau 5, 10, 20 phiên (chiều short tính theo chiều short); tính alpha so với SPY trên cùng khung thời gian; tính MFE/MAE (% và ATR); kiểm định tính đơn điệu của score (Top vs Bottom quartile); hiển thị trạng thái "Đang chờ (Pending)" khi chưa đủ phiên; hỗ trợ xuất CSV.
  - **Tích hợp Pipeline & Điều hướng Dashboard (`jobs/update_pipeline.py`, `app/main.py`):** Tích hợp tự động sinh sự kiện và đánh giá outcomes sau mỗi lần lưu snapshot. Tổ chức lại giao diện 7 tab tối giản: "00 Hôm nay" lên đầu, tiếp đến "01 Ứng viên", "02 Hiệu quả Tín hiệu", "03 Tổng quan Thị trường", "04 Xếp hạng Ngành", "05 Lịch sử Biến động", "06 Kiểm toán Dữ liệu".
- **Files / areas chạm:** `analytics/market_calendar.py`, `storage/database.py`, `storage/repository.py`, `analytics/market_breadth.py`, `analytics/setup_analyzer.py`, `analytics/screening_rules.py`, `analytics/signal_events.py`, `analytics/signal_outcomes.py`, `jobs/update_signal_outcomes.py`, `jobs/update_pipeline.py`, `app/components/setup_detail.py`, `app/components/today_dashboard.py`, `app/components/signal_performance.py`, `app/components/candidate_cards.py`, `app/main.py`, `tests/test_swing_features.py`, `tests/test_analytics.py`, `tests/test_storage.py`, `tests/test_pipeline_e2e.py`, `README.md`.
- **Verify:**
  - Bộ kiểm thử tự động toàn diện: `pytest` đạt **42/42 tests pass 100%** (30 tests cũ + 12 tests tính năng swing mới) trong 7.09s.
  - Chạy thực nghiệm `jobs/update_signal_outcomes.py`: nạp và theo dõi thành công 170 tín hiệu, đánh giá chính xác 510 forward outcomes (trạng thái pending cho các phiên chưa trôi qua).
  - Khởi chạy thành công ứng dụng Streamlit với tab Hôm nay và Hiệu quả tín hiệu trực quan.
- **Mode / Type / Action / Lane:** REFACTOR / ENHANCEMENT / EXECUTE / n/a
- **Tóm tắt:** Giải quyết triệt để toàn bộ 9 khoảng trống miền tài chính (Domain Gaps) được nêu trong `docs/domain-review-2026-09-08.md`: tính toán 1Y trung thực không fallback tùy tiện, phát hiện breakout nhân quả và phân biệt setup/trigger, kiểm soát session và data freshness theo America/New_York và giờ đóng cửa 16:00 ET, lưu trữ bền vững metadata ứng viên (score, rank, sub_industry, is_oneil_leader, industry_comp), bảo toàn dữ liệu FA qua `COALESCE` upsert, liên kết cảnh báo rủi ro BCTC (Earnings Event Risk <= 14 ngày), khắc phục phân loại 4 trạng thái ngành tránh gắn nhãn "Tụt hậu" sai lệch, bổ sung độ rộng và độ phân tán nhóm ngành, và chuẩn hóa đơn vị điểm phần trăm (% pts).
- **Thay đổi chính:**
  - **D-01 (1Y Ranking & Observation Counts):** Cập nhật `config/settings.py` nạp nến 2Y (`DEFAULT_FETCH_PERIOD = "2y"`); quy định bắt buộc đủ 253 quan sát cho 252d return (`analytics/market_breadth.py`). Tại `analytics/industry_ranker.py`, bảo toàn `None/NaN` cho rank 1Y và composite score nếu thiếu dữ liệu, tự động tái chuẩn hóa trọng số COMP/BLEND động qua các kỳ hạn hợp lệ.
  - **D-02 (Causal Breakout & Truthful Trend):** Thay thế `high20` bằng `prev_high20` (đỉnh 20 phiên trước) để kiểm tra breakout nhân quả; tách rõ trạng thái `confirmed` (đã breakout) và `setup` (tiệm cận chờ break); mô tả chính xác trạng thái MA50/MA200 khi MA50 chưa cắt lên MA200; bảo toàn trạng thái `watchlist` cho các ứng viên mâu thuẫn xu hướng tại `analytics/screening_rules.py`.
  - **D-03 (Session & Freshness Alignment):** Triển khai hàm `determine_target_trading_session` chuẩn xác theo múi giờ `America/New_York` và mốc 16:00 ET đóng cửa sàn NYSE/NASDAQ; loại bỏ các nến intraday chưa chốt phiên; kiểm tra đồng phiên với benchmark SPY; gắn nhãn trạng thái snapshot (`complete`, `degraded`, `failed`) tại `jobs/update_pipeline.py`.
  - **D-04 (Candidate Persistence & Ranking):** Bổ sung các cột `score`, `rank`, `sub_industry`, `is_oneil_leader`, `industry_comp` vào bảng `candidate_snapshots` và `coverage_252d`, `status` vào bảng `snapshots` (`storage/database.py` và migration an toàn). Cập nhật `storage/repository.py` bảo toàn thứ tự `ORDER BY group_type, score DESC, symbol ASC`.
  - **D-05 (Methodology Clarification):** Thêm banner chú thích phương pháp luận Market Radar RS lấy cảm hứng CANSLIM trên 127 GICS Sub-Industries; cổ phiếu dẫn dắt bắt buộc đồng thời thỏa mãn thuộc nhóm ngành dẫn dắt (COMP >= 80) VÀ bản thân cổ phiếu có RS vượt trội.
  - **D-06 (Small-Sample Tracking, Breadth & Sector States):** Bổ sung cờ `is_small_sample` cho nhóm ngành có <= 2 mã, hiển thị dấu `*` trên Heatmap, tính toán thêm lợi suất trung vị `median_perf_20d`, độ rộng nội bộ (`breadth_ma50_pct`, `breadth_ma20_pct`) và độ phân tán (`perf_20d_std`). Khắc phục logic 4 trạng thái ngành trong `analytics/sector_ranker.py` để ngành có RS dương nhưng độ rộng hẹp được xếp đúng vào "Suy yếu / Phân hóa", không bị quy chụp thành "Tụt hậu (Lagging)".
  - **D-07 (Earnings Event Risk & FA Preservation):** Tính toán số ngày đến kỳ công bố BCTC (`calculate_days_to_earnings`), kiểm tra `earningsTimestamp` phải nằm ở tương lai; gắn thẻ cảnh báo rủi ro biến động gap cao nếu <= 14 ngày vào ứng viên; nâng cấp `storage/repository.py` dùng `ON CONFLICT DO UPDATE ... COALESCE` bảo toàn giá trị FA hợp lệ khi cập nhật gặp sự cố mạng.
  - **D-08 (Market Breadth & Unit Standardization):** Chuyển nhãn đỉnh/đáy 20 phiên sang "Áp sát đỉnh/đáy 20 phiên" (<0.5%), bổ sung đếm số mã tăng/giảm (Advance/Decline), chỉnh sửa câu diễn giải RSP vs SPY thành tỷ trọng bình quân vs vốn hóa lớn trong S&P 500. Chuẩn hóa hiển thị đơn vị RS thành điểm phần trăm (`% pts`) tại `app/components/sector_table.py` và `metrics_cards.py`.
  - **D-09 (Verification Suite):** Bổ sung các bài kiểm thử đơn vị chuyên sâu mới cho từng gap miền (`tests/test_analytics.py`, `tests/test_storage.py`), nâng tổng số bài kiểm thử lên 25/25 pass 100%.
- **Files / areas chạm:** `config/settings.py`, `analytics/market_breadth.py`, `analytics/industry_ranker.py`, `analytics/sector_ranker.py`, `analytics/screening_rules.py`, `analytics/company_fa.py`, `storage/database.py`, `storage/repository.py`, `jobs/update_pipeline.py`, `providers/yfinance_provider.py`, `app/main.py`, `app/components/candidate_cards.py`, `app/components/industry_heatmap.py`, `app/components/sector_table.py`, `app/components/metrics_cards.py`, `SRS.md`, `tests/test_analytics.py`, `tests/test_storage.py`, `README.md`.
- **Verify:**
  - `python -m pytest -v`: 25/25 tests passed (100%) trong 1.81s.

### [2026-09-08] Triển khai Ma trận Nhóm ngành & Cổ phiếu Dẫn đầu theo William O'Neil (CANSLIM) `(EXE)`
- **Mode / Type / Action / Lane:** FEATURE / ENHANCEMENT / EXECUTE / n/a
- **Tóm tắt:** Hiện thực hóa trọn vẹn triết lý *"Focus on leading stocks in leading industry groups"* của William J. O'Neil: động cơ xếp hạng 127 Sub-Industries đa khung thời gian (Day, Wk, Mth, Qtr, 6M, 1Y) chuẩn hóa Percentile 1-99, điểm Composite RS (`COMP`) và `BLEND`, bảng Heatmap tương tác với các pill cổ phiếu dẫn đầu có mã màu phiên và link 1-click TradingView, tích hợp nhãn ⭐ O'Neil Leader cho ứng viên swing trade.
- **Thay đổi chính:**
  - **Config & Tham số Kỹ thuật:** Bổ sung chu kỳ nến 6M/1Y, cấu hình trọng số O'Neil CANSLIM cho `COMP` và `BLEND`, ngưỡng nhóm dẫn dắt `LEADING_GROUP_THRESHOLD = 80` tại `config/settings.py`.
  - **Stock RS Rating:** Bổ sung tính toán `perf_126d`, `perf_252d` và Stock RS Rating cá nhân (1-99) chuẩn hóa phân vị tại `analytics/market_breadth.py`.
  - **Động cơ Industry Ranker:** Xây dựng mới `analytics/industry_ranker.py` tính toán hiệu suất Equal-Weighted cho 127 nhóm ngành, chuẩn hóa điểm Percentile 1-99 trên 6 khung thời gian, tính `COMP`/`BLEND` và trích xuất danh sách cổ phiếu dẫn đầu theo ngành.
  - **Nhận diện O'Neil Leader:** Cập nhật `analytics/screening_rules.py` tự động phát hiện và gắn nhãn ⭐ O'Neil Leader (thuộc Top 20% nhóm ngành mạnh nhất), cộng điểm ưu tiên cho ứng viên nhóm Long.
  - **Lưu trữ & Migration:** Cập nhật `storage/database.py` bổ sung cơ chế Safe Migration tự động thêm cột `industry_metrics TEXT` cho database cũ; cập nhật `storage/repository.py` để lưu và tải `industry_metrics`.
  - **Pipeline:** Tích hợp `rank_industry_groups` vào `jobs/update_pipeline.py`.
  - **Giao diện Heatmap O'Neil:** Xây dựng mới `app/components/industry_heatmap.py` với ma trận nhiệt đổi màu theo điểm số, pill cổ phiếu xanh/đỏ link TradingView, bộ lọc tìm kiếm và lọc Top 20% ngành; tích hợp vào Sub-tab Tab 2 và bộ lọc tại Tab 3 trong `app/main.py` và `candidate_cards.py`.
- **Files / areas chạm:** `config/settings.py`, `analytics/market_breadth.py`, `analytics/industry_ranker.py`, `analytics/screening_rules.py`, `storage/database.py`, `storage/repository.py`, `jobs/update_pipeline.py`, `app/components/industry_heatmap.py`, `app/components/sector_table.py`, `app/components/candidate_cards.py`, `app/main.py`, `tests/test_analytics.py`, `tests/test_storage.py`, `README.md`.
- **Verify:**
  - `pytest tests/ -v` đạt **13/13 tests pass 100%** trong 1.14s.
  - Kiểm thử thực tế trên 129,620 nến ngày của 503 mã: xếp hạng thành công 127 nhóm ngành với Top 1 là *Oil & Gas Refining & Marketing* (COMP: 99), *Biotechnology* (COMP: 98), *Technology Hardware* (COMP: 97, top SNDK +11.9%, DELL +1.5%), khớp hoàn hảo với dữ liệu và ảnh tham chiếu.
  - Snapshot #3 tạo thành công đầy đủ 127 nhóm ngành và 170 ứng viên.

### [2026-09-05] Khởi tạo trọn vẹn Market Radar MVP `(INIT)`
- **Mode / Type / Action / Lane:** INIT / n/a / EXECUTE / n/a
- **Tóm tắt:** Xây dựng hoàn chỉnh dashboard Market Radar chạy cục bộ với chi phí dữ liệu 0đ: từ kiểm chứng P0, kiến trúc SQLite, động cơ phân tích độ rộng S&P 500, xếp hạng 11 ngành GICS, sàng lọc 4 nhóm ứng viên swing trade đến giao diện Streamlit đa tab kết nối TradingView.
- **Thay đổi chính:**
  - **P0 Feasibility Probe:** Nghiên cứu và chứng minh tính khả thi nguồn dữ liệu mở: Wikipedia cho danh sách S&P 500 (503 mã) và Yahoo Finance cho nến ngày và FA/Earnings.
  - **P1 Data & Storage:** Xây dựng `storage/database.py`, `storage/repository.py` (WAL mode, foreign keys), `storage/lock.py` (ProcessLock). Xây dựng `providers/sp500_provider.py` và `providers/yfinance_provider.py` với tính năng tải đa luồng `ThreadPoolExecutor`.
  - **P2 Market & Sector Analytics:** Xây dựng `analytics/market_breadth.py` (MA20/50/200, Advance/Decline, Net High/Low, phân kỳ đà tăng SPY vs RSP) và `analytics/sector_ranker.py` (Relative Strength 1W/1M/3M, xếp hạng 4 trạng thái, breakdown nhóm ngành nhỏ).
  - **P3 Stock Screening Engine:** Xây dựng `analytics/screening_rules.py` phân loại 4 nhóm ứng viên (Long Tiếp Diễn, Short Tiếp Diễn, Long Đảo Chiều, Short Đảo Chiều), bộ lọc loại trừ tín hiệu mâu thuẫn và không ép hạn ngạch. Xây dựng `analytics/company_fa.py` với cơ chế nhận diện đặc thù tài chính/ngân hàng.
  - **P4 Streamlit Dashboard:** Xây dựng `app/main.py` và các component trực quan hóa (`metrics_cards.py`, `sector_table.py`, `candidate_cards.py`), tích hợp nút cập nhật thủ công, so sánh lịch sử snapshot và nút mở trực tiếp TradingView.
  - **P5 Testing & Seed Run:** Viết bộ 11 unit & integration tests (`pytest tests/ -v` đạt 100% pass); chạy thực tế 2 snapshot nạp đủ 129,620 nến ngày với độ bao phủ 100.0% (503/503 mã).
- **Files / areas chạm:** `config/`, `storage/`, `providers/`, `analytics/`, `jobs/`, `app/`, `tests/`, `.env.example`, `.gitignore`, `requirements.txt`, `README.md`.
- **Ảnh hưởng README:** §1, §2, §3, §4, §5 (khởi tạo đầy đủ theo chuẩn vibecode-flow).
- **Verify:**
  - 11/11 tests pass trong 3.38s: `pytest tests/ -v`
  - Chạy thành công chu trình cập nhật 2 snapshot thực tế với độ phủ 100% (503/503 mã S&P 500) lưu vào `data/market_radar.db`.
- **Notes / nợ kỹ thuật:** Đã tối ưu tốc độ tải FA cho các mã ứng viên bằng `ThreadPoolExecutor` (10 workers) giúp chu kỳ cập nhật rút ngắn xuống ~100 giây.

---

## 5. Các task chưa làm
| ID | Hạng mục backlog | Mức ưu tiên | Ghi chú kỹ thuật |
|---|---|---|---|
| B01 | Trailing Stop & Take-Profit Simulation Engine | Thấp (Ý tưởng) | Mô phỏng đường thoát lệnh trailing stop theo ATR14 hoặc MA20 để so sánh với fixed-horizon outcomes |
| B02 | Tích hợp Webhook Alert tự động (Telegram / Discord) | Thấp (Tiện ích) | Bắn thông báo tóm tắt buổi sáng (08:00 ICT) về các sự kiện mới xuất hiện trên trang Hôm Nay |
| B03 | Tải trước dữ liệu nến tuần (Weekly Bars Caching) | Thấp (Tối ưu) | Lưu trữ bảng riêng cho nến tuần đã chốt để tăng tốc độ phân tích bối cảnh đa khung |

---

## Tác giả / Bản quyền
Dự án Market Radar — Thiết kế phục vụ phân tích cá nhân cho swing trading S&P 500.
