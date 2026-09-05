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

# 3. Khởi chạy Dashboard Streamlit
streamlit run app/main.py

# 4. Chạy kiểm thử tự động
pytest tests/ -v
```

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
| M01 | Tổng quan thị trường | Hiệu suất SPY/RSP; tỷ lệ cổ phiếu trên MA20/50/200; số mã Advance/Decline; đỉnh/đáy 20 phiên; cảnh báo phân kỳ tập trung đà tăng (Breadth divergence) | done |
| M02 | Xếp hạng ngành | Xếp hạng 11 nhóm ngành GICS theo Relative Strength (1W, 1M, 3M) vs SPY và độ rộng ngành (% trên MA50); phân loại 4 trạng thái (Leading, Improving, Weakening, Lagging) | done |
| M03 | Nhóm ngành nhỏ | Drill-down xem chi tiết các Sub-Industry trong từng ngành, số mã thành phần, lợi suất trung bình và mã dẫn đầu | done |
| M04 | 4 nhóm ứng viên giao dịch | Sàng lọc 4 nhóm ứng viên swing trade: Long Tiếp Diễn, Short Tiếp Diễn, Long Đảo Chiều, Short Đảo Chiều; có Watchlist cho tín hiệu mâu thuẫn; không ép hạn ngạch | done |
| M05 | Chi tiết cổ phiếu & TradingView | Thẻ giải trình chi tiết lý do kỹ thuật (MA, RS, Volume), bối cảnh FA doanh nghiệp (Doanh thu, EPS, Biên LN, đặc thù dòng tiền/nợ ngân hàng), lịch Earnings, nút 1-click mở TradingView | done |
| M06 | Thay đổi và lịch sử | Lưu trữ snapshot SQLite mỗi chu kỳ; so sánh biến động giữa các snapshot: mã mới lọt/rời danh sách, biến động thứ hạng ngành; hỗ trợ xuất CSV | done |
| M07 | Chất lượng dữ liệu & 0đ | Nguồn mở 100% (Wikipedia + Yahoo Finance), giám sát thời điểm `as_of`, tỷ lệ bao phủ (>95%), danh sách mã lỗi, cơ chế ProcessLock chống chạy trùng | done |

### Chi tiết các luồng chính
- **M01 — Thị trường:** Tóm tắt tự động bằng câu văn có số liệu thực tế; phát hiện nhanh đà tăng do nhóm vốn hóa lớn kéo hay lan tỏa toàn thị trường (so sánh SPY vs RSP).
- **M02 & M03 — Ngành:** Biểu đồ ngang tương tác Plotly thể hiện RS 1 Tháng của 11 ngành so với SPY, kèm bảng dữ liệu và danh sách chi tiết nhóm ngành nhỏ.
- **M04 & M05 — Ứng viên:** 4 tab chuyên biệt cho 4 chiến thuật swing. Mỗi mã có thẻ bằng chứng kỹ thuật và gắn cờ cơ bản. Với các mã Short luôn có nhãn cảnh báo *"Chưa xác minh khả năng short / phí vay"*.
- **M06 — Lịch sử:** Cho phép chọn xem lại các snapshot cũ trong sidebar và hiển thị bảng so sánh delta trực quan.

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
        ├──> [analytics/market_breadth] ──> [Market Overview & Breadth]
        ├──> [analytics/sector_ranker]  ──> [11 GICS Sectors Ranking]
        ├──> [analytics/screening_rules]──> [4 Candidate Groups + Watchlist]
        └──> [analytics/company_fa]     ──> [FA Flags & Earnings Status]
                     │
                     ▼
             [app/main.py (Streamlit)] ──> [1-Click TradingView Charts]
```

### Cấu trúc thư mục
```text
market radar/
├── app/                          # Giao diện ứng dụng Streamlit
│   ├── main.py                   # Entry point Dashboard đa tab
│   └── components/               # Các UI components tái sử dụng
│       ├── metrics_cards.py      # Bức tranh thị trường, độ rộng, SPY vs RSP
│       ├── sector_table.py       # Xếp hạng 11 ngành, biểu đồ RS, Sub-industry
│       └── candidate_cards.py    # Thẻ ứng viên 4 nhóm, TA reasons, FA flags, link TV
├── providers/                    # Adapter kết nối và thu thập dữ liệu
│   ├── base.py                   # Interface trừu tượng BaseUniverse & BaseMarketData
│   ├── sp500_provider.py         # Lấy danh sách S&P 500 & phân ngành từ Wikipedia
│   └── yfinance_provider.py      # Tải batch nến ngày, ETF và FA/Earnings song song
├── storage/                      # Cơ sở dữ liệu và lưu trữ
│   ├── database.py               # Kết nối SQLite & định nghĩa Schema 5 bảng
│   ├── repository.py             # CRUD: universe, bars, fundamentals, snapshots, diff
│   └── lock.py                   # Khóa tiến trình chống chạy đồng thời (ProcessLock)
├── analytics/                    # Động cơ phân tích định lượng & sàng lọc
│   ├── market_breadth.py         # Tính MA20/50/200, độ rộng, A/D, SPY vs RSP divergence
│   ├── sector_ranker.py          # Relative strength 1W/1M/3M, xếp hạng ngành, 4 trạng thái
│   ├── screening_rules.py        # Luật sàng lọc 4 nhóm ứng viên, lọc mâu thuẫn
│   └── company_fa.py             # Đánh giá FA, cảnh báo đòn bẩy, ngoại lệ ngân hàng
├── jobs/                         # Tác vụ cập nhật dữ liệu tự động
│   └── update_pipeline.py        # Pipeline cập nhật toàn diện và tạo snapshot
├── config/                       # Tham số cấu hình
│   ├── settings.py               # Ngưỡng kỹ thuật (MA, RS, Volume, Coverage)
│   └── sector_mappings.py        # Bản đồ 11 GICS Sectors <-> 11 SPDR Sector ETFs
├── data/                         # Thư mục chứa cơ sở dữ liệu SQLite local
│   └── market_radar.db
├── tests/                        # Bộ kiểm thử tự động
│   ├── test_providers.py         # Kiểm tra adapter và chuẩn hóa ký hiệu
│   ├── test_analytics.py         # Kiểm tra tính toán kỹ thuật và quy tắc ứng viên
│   ├── test_storage.py           # Kiểm tra database SQLite, CRUD và snapshot diff
│   └── test_pipeline_e2e.py      # Kiểm tra tích hợp toàn diện trên database thực tế
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## 3. Các component

| Component / Module | Path | Vai trò | Phụ thuộc chính |
|---|---|---|---|
| **App Entry Point** | `app/main.py` | Giao diện chính Streamlit, điều hướng 5 tab, nút cập nhật và xuất CSV | `streamlit`, `storage/repository` |
| **Market Metrics UI** | `app/components/metrics_cards.py` | Hiển thị thẻ độ rộng thị trường, phân kỳ SPY vs RSP, gauge MA50 | `plotly`, `streamlit` |
| **Sector Table UI** | `app/components/sector_table.py` | Bảng xếp hạng ngành, biểu đồ thanh RS, drill-down Sub-industry | `plotly`, `streamlit`, `pandas` |
| **Candidate Cards UI** | `app/components/candidate_cards.py` | Hiển thị thẻ ứng viên 4 nhóm, giải trình TA, cờ FA, link TradingView | `streamlit` |
| **Universe Provider** | `providers/sp500_provider.py` | Thu thập 503 mã S&P 500 và 11 GICS ngành từ Wikipedia | `requests`, `pandas`, `lxml` |
| **Market Data Provider**| `providers/yfinance_provider.py` | Tải batch OHLCV daily và FA/Earnings song song (ThreadPoolExecutor) | `yfinance`, `pandas` |
| **Database Schema** | `storage/database.py` | Quản lý kết nối SQLite WAL và khởi tạo bảng | `sqlite3` |
| **Data Repository** | `storage/repository.py` | Thực thi truy vấn, lưu snapshot, tính diff giữa 2 snapshot | `sqlite3`, `pandas` |
| **Process Lock** | `storage/lock.py` | File lock bảo vệ pipeline không chạy đè lên nhau | `os`, `pathlib` |
| **Market Breadth** | `analytics/market_breadth.py`| Tính MA20/50/200, độ rộng thị trường, Advance/Decline, SPY vs RSP | `numpy`, `pandas` |
| **Sector Ranker** | `analytics/sector_ranker.py` | Tính RS 1W/1M/3M, phân loại Leading/Improving/Weakening/Lagging | `pandas` |
| **Screening Rules** | `analytics/screening_rules.py` | Sàng lọc 4 nhóm ứng viên, lọc mâu thuẫn kỹ thuật, hỗ trợ danh sách rỗng | `pandas`, `config` |
| **FA Evaluator** | `analytics/company_fa.py` | Đánh giá tăng trưởng, cảnh báo đòn bẩy, loại trừ ngân hàng, lịch earnings | `pandas` |
| **Update Pipeline** | `jobs/update_pipeline.py` | Điều phối chu trình cập nhật trọn vẹn: fetch -> compute -> save snapshot | Toàn bộ providers & analytics |

---

## 4. Các task đã làm

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

*(Bảng backlog để trống theo quy tắc khởi tạo INIT lần đầu chuẩn vibecode-flow)*

---

## Tác giả / Bản quyền
Dự án Market Radar — Thiết kế phục vụ phân tích cá nhân cho swing trading S&P 500.
