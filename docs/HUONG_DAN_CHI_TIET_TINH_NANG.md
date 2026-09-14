# MARKET RADAR — HƯỚNG DẪN CHI TIẾT TỪNG TÍNH NĂNG
## BẢNG TRA CỨU TÍNH NĂNG HỆ THỐNG (FEATURE MANUAL)

---

> **Tên hệ thống:** Market Radar — S&P 500 Top-Down Swing Trading Radar  
> **Phiên bản kiến trúc:** 2.1 (Editorial Utilitarian Minimalism / Light Theme)  
> **Mục tiêu:** Cung cấp trạm làm việc phân tích thị trường chứng khoán Mỹ theo phương pháp Top-Down, dẫn dắt từ bức tranh vĩ mô/độ rộng S&P 500, qua 11 nhóm ngành GICS và 127 nhóm ngành O'Neil, đến danh sách ứng viên Swing Trading chất lượng cao với chi phí dữ liệu 0 đồng.

---

## MỤC LỤC

1. [TỔNG QUAN KIẾN TRÚC & GIAO DIỆN HỆ THỐNG](#1-tổng-quan-kiến-trúc--giao-diện-hệ-thống)
   - 1.1 Triết lý thiết kế Utilitarian Minimalist & Light Theme
   - 1.2 Kiến trúc Điều hướng 2 cấp (Two-Tier Navigation Architecture)
   - 1.3 Thanh Sidebar: Quản lý Snapshot & Trạng thái Vận hành
   - 1.4 Khối Đồng hồ Thị trường & Giám sát Độ tươi Dữ liệu
2. [TRỤ CỘT 1: 🎯 HÔM NAY & ỨNG VIÊN](#2-trụ-cột-1--hôm-nay--ứng-viên)
   - 2.1 Góc nhìn 01: Hôm Nay (Sự Kiện & Biến Động Liên Phiên)
   - 2.2 Góc nhìn 02: Ứng Viên Giao Dịch (4 Nhóm Swing & Watchlist)
   - 2.3 Bảng So Sánh Trực Diện 2–5 Ứng Viên (Side-by-Side Comparison)
   - 2.4 Góc nhìn 03: Phân Hệ Lịch Báo Cáo Tài Chính (Earnings Calendar)
   - 2.5 Hộp Thoại Chi Tiết Setup (Setup Detail Dialog — 3 Tabs Nội Bộ)
3. [TRỤ CỘT 2: 🌐 BẢN ĐỒ THỊ TRƯỜNG & NGÀNH](#3-trụ-cột-2--bản-đồ-thị-trường--ngành)
   - 3.1 Góc nhìn 01: Bức Tranh Thị Trường & Độ Rộng Tham Gia
   - 3.2 Cụm Biểu Đồ Nến 3 Chỉ Số Lớn (S&P 500, NASDAQ, DOW)
   - 3.3 5 Thanh Bar Đối Chiếu Tỷ Lệ Độ Rộng Thị Trường
   - 3.4 Phân Kỳ Vốn Hóa (SPY vs RSP) & Chuỗi Thời Gian Độ Rộng
   - 3.5 Góc nhìn 02: 11 Ngành GICS (Sector Rotation & Health)
   - 3.6 Biểu Đồ Luân Chuyển 4 Góc Phần Tư RRG & Vệt Lịch Sử 10 Phiên
   - 3.7 Đánh Giá Sức Khỏe Nội Bộ Ngành & Cảnh Báo Mega-Cap Masking
   - 3.8 Góc nhìn 03: Ma Trận 127 Nhóm Ngành O'Neil (CANSLIM Percentile Matrix)
4. [TRỤ CỘT 3: 📊 ĐO LƯỜNG & KIỂM TOÁN](#4-trụ-cột-3--đo-lường--kiểm-toán)
   - 4.1 Góc nhìn 01: Hiệu Quả Tín Hiệu (Alpha Audit & Forward Outcomes)
   - 4.2 Đo Lường Swing Trong Tuần (In-Week Swing & Week-Close 99)
   - 4.3 Khảo Sát Lợi Thế Nến Nhật (Candlestick Edge Audit)
   - 4.4 Kiểm Định Tính Đơn Điệu Của Score (Top vs Bottom Quartile)
   - 4.5 Góc nhìn 02: So Sánh Biến Động Snapshot (Delta History)
   - 4.6 Góc nhìn 03: Giám Sát Chất Lượng Dữ Liệu & Nguyên Tắc 0 Đồng
5. [TÍCH HỢP NGOÀI & XUẤT DỮ LIỆU](#5-tích-hợp-ngoài--xuất-dữ-liệu)
   - 5.1 Tích hợp biểu đồ TradingView 1-Click
   - 5.2 Tra cứu hồ sơ pháp lý SEC EDGAR 1-Click
   - 5.3 Xuất file CSV phục vụ Nhật ký Giao dịch (Trading Journal / Excel)

---

## 1. TỔNG QUAN KIẾN TRÚC & GIAO DIỆN HỆ THỐNG

### 1.1 Triết lý thiết kế Utilitarian Minimalist & Light Theme
Market Radar được xây dựng theo phong cách **Editorial Utilitarian Minimalism**:
- **Bảng màu Light Theme chuẩn mực:** Nền giấy trắng xám `#FBFBFA` / `#FFFFFF`, chữ đen sâu `#111111` và xám trung tính `#787774`, đường viền tinh gọn `#EAEAEA`.
- **Không chi tiết thừa:** Không dùng gradient bóng bẩy, không hiệu ứng đổ bóng nặng nề, tập trung hoàn toàn vào mật độ thông tin cao và sự chính xác của số liệu.
- **Font chữ kỹ thuật số:** Sử dụng bộ font Geist / Geist Mono và Inter, hỗ trợ hiển thị số dạng tabular (`tabular-nums`) giúp việc so sánh số liệu tài chính thẳng hàng tuyệt đối.

### 1.2 Kiến trúc Điều hướng 2 cấp (Two-Tier Navigation Architecture)
Hệ thống tổ chức toàn bộ phân tích nghiệp vụ thành **3 Trụ Cột (Pillars)** chính ở Cấp 1, bên dưới mỗi Trụ Cột là **3 Góc Nhìn (Sub-views)** ở Cấp 2, sử dụng thanh điều hướng `segmented_control` hiện đại:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ TRẠM LÀM VIỆC CHÍNH (CẤP 1):                                           │
│ [ 🎯 Hôm Nay & Ứng Viên ]   [ 🌐 Bản Đồ Thị Trường & Ngành ]   [ 📊 Đo Lường & Kiểm Toán ] │
└────────────────────────────────────────────────────────────────────────┘
          │                               │                               │
          ▼                               ▼                               ▼
┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
│ GÓC NHÌN CẤP 2:  │           │ GÓC NHÌN CẤP 2:  │           │ GÓC NHÌN CẤP 2:  │
│ 01 Hôm Nay       │           │ 01 Bức Tranh Mkt │           │ 01 Hiệu Quả T.Hiệu│
│ 02 Ứng Viên GD   │           │ 02 11 Ngành GICS │           │ 02 So Sánh Snap  │
│ 03 Lịch BCTC     │           │ 03 127 Ngành O'N │           │ 03 Kiểm Toán Data│
└──────────────────┘           └──────────────────┘           └──────────────────┘
```

> **Lợi ích kiến trúc:** Ứng dụng chỉ render duy nhất trạm làm việc và góc nhìn đang được chọn, loại bỏ hoàn toàn hiện tượng lag trình duyệt do phải nạp hàng chục biểu đồ cùng lúc.

---

### 1.3 Thanh Sidebar: Quản lý Snapshot & Trạng thái Vận hành
Nằm ở cạnh trái màn hình, thanh Sidebar cung cấp bảng điều khiển trung tâm về dữ liệu:

1. **Nút "Cập nhật dữ liệu ngay" (Primary Button):**
   - Kích hoạt pipeline nạp dữ liệu tức thời: Tải danh mục S&P 500 từ Wikipedia, tải giá nến ngày EOD và dữ liệu FA từ Yahoo Finance, tính toán toàn bộ chỉ số kỹ thuật, tạo snapshot mới và cập nhật kết quả tín hiệu.
   - Hiển thị spinner trạng thái và thông báo thành công kèm mã Snapshot ID mới (`Snapshot #X`).
2. **Hộp chọn "Lịch sử Snapshot":**
   - Cho phép quay ngược thời gian để xem lại tối đa 20 snapshot gần nhất.
   - Mỗi lựa chọn hiển thị rõ: Mã ID, ngày giao dịch (`as_of`), và tỷ lệ bao phủ dữ liệu đồng phiên (ví dụ: `#14 (2026-09-11) · Phủ 98.4%`).
3. **Thẻ "Trạng thái Dữ liệu":**
   - **Huy hiệu trạng thái (Status Badge):**
     - `Complete (Đồng phiên)` (Xanh lá): Dữ liệu đồng nhất, đủ nến lịch sử và tỷ lệ bao phủ $\ge 95\%$.
     - `Cũ (X phiên)` (Vàng hổ phách hoặc Đỏ): Cảnh báo snapshot đang xem đã chậm $X$ phiên so với lịch giao dịch thực tế của NYSE.
     - `Degraded` (Đỏ nhạt): Tỷ lệ bao phủ dưới ngưỡng chuẩn ($<95\%$).
     - `Legacy Snapshot` / `Lỗi Bất Biến`: Dữ liệu cũ trước đợt nâng cấp schema hoặc số mã hợp lệ vượt tổng vũ trụ.
   - **Thông số kỹ thuật:**
     - `Thời điểm (As of)`: Ngày chốt phiên giao dịch của dữ liệu.
     - `Độ bao phủ đồng phiên`: Số mã có nến đóng cửa đúng ngày `as_of` trên tổng 503 mã S&P 500.
     - `Đủ lịch sử 1Y (≥250 nến)`: Tỷ lệ cổ phiếu có đủ chuỗi dữ liệu 1 năm để tính toán các đường trung bình dài hạn (MA200).
   - **Tuyên bố phạm vi vũ trụ:** Khẳng định rõ hệ thống chỉ quét trong phạm vi **503 mã cổ phiếu vốn hóa lớn (Large Cap) thuộc S&P 500**, không bao gồm penny, OTC hay ~8.000 cổ phiếu nhỏ ngoài chỉ số.
4. **Nút "Xuất danh sách Ứng viên (CSV cho Excel)":**
   - Nút download trực tiếp toàn bộ danh sách cổ phiếu đạt tiêu chuẩn của snapshot hiện tại thành file CSV (bao gồm Rank, Symbol, Group, Setup, Price, Trigger, Invalidation, ATR, Performance).

---

### 1.4 Khối Đồng hồ Thị trường & Giám sát Độ tươi Dữ liệu
Hai thẻ thông tin nằm ngay trên đầu giao diện chính cung cấp bối cảnh thời gian thực:

1. **Thẻ Đồng Hồ Thị Trường & Trạng Thái NYSE:**
   - **Thời gian kép:** Hiển thị song song giờ **New York (ET)** và giờ **Việt Nam (ICT)** với font monospaced.
   - **Huy hiệu trạng thái phiên:** Tự động đối chiếu lịch NYSE (tính cả ngày nghỉ lễ liên bang và các phiên đóng cửa sớm lúc 13:00 ET):
     - `Đang Mở Cửa` (Regular Trading: 09:30 – 16:00 ET).
     - `Tiền Thị Trường` (Pre-market: 04:00 – 09:30 ET).
     - `Sau Giờ Đóng Cửa` (After-hours / Post-market: 16:00 – 20:00 ET).
     - `Thị Trường Đóng Cửa` (Weekend / Holiday / Night).
     - `Đóng Cửa Sớm (13:00 ET)`: Vào các phiên đặc biệt như sau Lễ Tạ Ơn (Black Friday) hoặc trước Giáng Sinh.
   - **Mục tiêu phiên:** Cho biết phiên giao dịch gần nhất mà hệ thống đang hướng tới.
2. **Thẻ Độ Tươi Dữ Liệu & Phạm Vi Vũ Trụ:**
   - Đánh giá chênh lệch giữa ngày của snapshot đang xem với phiên giao dịch gần nhất đã kết thúc của NYSE.
   - Huy hiệu `Phiên Mới Nhất` (Xanh lá) hoặc `Dữ Liệu Lịch Sử (Chậm X Phiên)` (Vàng/Đỏ).
   - Khi dữ liệu bị chậm phiên, hệ thống tự động bật **Hard-Gate Banner** cảnh báo người dùng không sử dụng danh sách ứng viên lịch sử để ra quyết định cho phiên hôm nay mà cần bấm nút cập nhật.

---

## 2. TRỤ CỘT 1: 🎯 HÔM NAY & ỨNG VIÊN

Trụ cột vận hành cốt lõi dành cho việc tìm kiếm cơ hội, kiểm tra tín hiệu mới và quản trị rủi ro vào lệnh.

---

### 2.1 Góc nhìn 01: Hôm Nay (Sự Kiện & Biến Động Liên Phiên)
Bàn làm việc đầu ngày giúp nhà giao dịch trả lời ngay câu hỏi: *"Phiên vừa qua có gì thay đổi so với phiên trước?"*. Hệ thống tự động so sánh snapshot hiện tại với snapshot liền trước để sinh ra 4 nhóm sự kiện chuẩn hóa:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [01 Cơ Hội Mới (N)]   [02 Thay Đổi Setup (N)]   [03 Sự Kiện BCTC (N)]   [04 Biến Động Ngành (N)] │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Phân loại 4 nhóm sự kiện:**
   - **01 Cơ Hội Mới (`new_candidate`):** Cổ phiếu mới lọt vào danh sách đạt chuẩn của 4 nhóm chiến thuật swing.
   - **02 Thay Đổi Setup (`setup_triggered`, `setup_invalidated`):** Cổ phiếu chuyển từ trạng thái theo dõi (`setup`) sang kích hoạt điểm vào lệnh (`confirmed`), hoặc bị vi phạm mức dừng lỗ/mất điều kiện kỹ thuật.
   - **03 Sự Kiện Sắp Tới (`earnings_upcoming`):** Cảnh báo các ứng viên Radar sắp công bố BCTC trong vòng 14 ngày tới.
   - **04 Biến Động Thị Trường & Ngành (`sector_rank_shift`, `market_breadth_shift`):** Các ngành dịch chuyển thứ hạng lớn ($\ge 2$ bậc) hoặc độ rộng thị trường đổi màu rõ rệt.
2. **Cấu trúc thẻ sự kiện chuẩn mực:**
   - **Huy hiệu mức độ:** `CƠ HỘI` (Xanh lá), `LƯU Ý` (Vàng), `RỦI RO` (Đỏ nhạt), `THÔNG TIN` (Xám).
   - **Tiêu đề & Tóm tắt:** Giải thích rõ ràng nguyên nhân biến động bằng ngôn ngữ tài chính chuẩn mực.
   - **Bằng chứng số liệu:** Trích dẫn chính xác giá trị kỹ thuật (ví dụ: `Volume: 2.1x SMA20 vol · Giá vượt đỉnh $185.50`).
   - **Phân tách xuất xứ & Mức độ tin cậy:**
     - *Tín hiệu Scanner EOD:* Xuất xứ từ thuật toán quét kỹ thuật nội bộ, có độ tin cậy tuyệt đối dựa trên giá đóng cửa.
     - *Sự kiện Doanh nghiệp / Lịch BCTC:* Xuất xứ từ Yahoo Finance Calendar. Hệ thống tự động gắn nhãn cảnh báo: `⚠️ Lịch ước tính (Chưa xác minh SEC/IR) - Đối chiếu trang IR công ty trước khi giải ngân`.
3. **Thanh công cụ tác vụ (Action Bar):**
   - Nút `TradingView (Ticker)`: Mở biểu đồ kỹ thuật nến ngày trực tiếp trên TradingView.
   - Nút `Tra cứu SEC EDGAR ↗`: Mở trang tra cứu hồ sơ 10-Q/10-K/8-K chính thức tại Ủy ban Chứng khoán Mỹ.
   - Nút `Đã đọc ✓`: Đánh dấu sự kiện đã được rà soát (sự kiện sẽ đổi màu nền xám nhẹ, giảm badge chưa đọc).
   - Nút `Chi tiết setup 🔍`: Mở modal phân tích toàn diện 3 tab cho cổ phiếu đó.
   - Nút `Đánh dấu tất cả đã đọc ✓` và bộ lọc trạng thái đọc (Tất cả / Mới / Đã đọc).

---

### 2.2 Góc nhìn 02: Ứng Viên Giao Dịch (4 Nhóm Swing & Watchlist)
Hệ thống sàng lọc toàn bộ 503 mã cổ phiếu S&P 500 thành **4 Nhóm Chiến Thuật Chuyên Biệt** và 1 Nhóm Theo Dõi. **Tuyệt đối không ép hạn ngạch:** Nếu thị trường không có cơ hội đạt chuẩn, danh sách sẽ trả về 0 mã thay vì đưa ra cổ phiếu kém chất lượng.

#### Bảng Quy Tắc Sàng Lọc 4 Nhóm Ứng Viên:

| Nhóm Chiến Thuật | Mã Nhóm | Điều Kiện Xu Hướng (Trend) | Điều Kiện Sức Mạnh (RS vs SPY) | Điểm Kích Hoạt (Triggers) | Subtypes Phân Loại |
|---|---|---|---|---|---|
| **Long Tiếp Diễn** | `long_cont` | Close > MA50; Close > MA200; MA20 $\ge$ MA50 | RS 1M > 0 (vượt trội SPY) và RS vs ETF ngành $\ge 0$ | Vượt đỉnh 20 phiên kèm Vol $\ge 1.5$x SMA20, hoặc Pullback chạm MA20/MA50 | `breakout`<br>`near_breakout`<br>`pullback_ma20`<br>`pullback_ma50` |
| **Short Tiếp Diễn** | `short_cont` | Close < MA50; Close < MA200; MA20 $\le$ MA50 | RS 1M < 0 (yếu hơn SPY) và RS vs ETF ngành $\le 0$ | Thủng đáy 20 phiên kèm Vol $\ge 1.0$x SMA20, hoặc hồi phục chạm cản MA20 | `breakdown`<br>`near_breakdown`<br>`pullback_ma20_res` |
| **Long Đảo Chiều** | `long_rev` | Nến trước nằm dưới MA20 hoặc MA50 (chuỗi giảm sâu) | Không yêu cầu RS dương, nhưng RS $\ge -2.0\%$ | Vượt trở lại trên MA20 kèm Vol $\ge 1.5$x, hoặc hồi phục $>2\%$ từ đáy 20 phiên | `reversal_reclaim`<br>`reversal_rebound` |
| **Short Đảo Chiều** | `short_rev` | Nến trước nằm trên MA20 hoặc MA50 (chuỗi tăng nóng) | Không yêu cầu RS âm, nhưng hiệu suất 5 phiên gần nhất suy yếu | Gãy xuống dưới MA20 kèm Vol $\ge 1.1$x, hoặc thoái lui $>4\%$ từ đỉnh 20 phiên | `reversal_drop`<br>`reversal_pullback` |
| **Danh Sách Theo Dõi** | `watchlist` | Xuất hiện tín hiệu mâu thuẫn giữa xu hướng lớn và nhịp chỉnh ngắn hạn | Bị loại khỏi danh sách ưu tiên hành động | Đưa vào quan sát, chờ hành vi giá xác nhận | `contradiction` |

#### Thành phần trên Thẻ Ứng Viên (Candidate Bento Card):
- **Phần đầu thẻ:** Thứ hạng (`#Rank`), Mã cổ phiếu (`Symbol`), Tên công ty, Ngành GICS, Phân ngành nhỏ, Huy hiệu `⭐ LEADER` (nếu thuộc Top 20% nhóm ngành O'Neil mạnh nhất), Điểm số tổng hợp (`Score`), và Trạng thái (`Triggered` - đã kích hoạt; `Setup` - đang hình thành; `Watchlist` - theo dõi).
- **Hàng chỉ số hiệu suất:** Giá đóng cửa hiện tại, Lợi suất 1D, 1W (5 phiên), 1M (20 phiên) hiển thị màu xanh lá/đỏ.
- **Cột Bằng chứng Kỹ thuật (TA):** Liệt kê chi tiết cấu trúc MA, điểm chênh lệch RS so với SPY và ETF ngành, hành vi khối lượng so với bình quân 20 phiên. Với mã Short, luôn có dòng lưu ý bắt buộc: `⚠️ Lưu ý Short: Chưa xác minh khả năng short / phí vay thực tế tại broker`.
- **Cột Bối cảnh Cơ bản (FA):** Hiển thị tăng trưởng Doanh thu YoY, tăng trưởng EPS YoY, Biên lợi nhuận ròng, kỳ BCTC gần nhất, và cảnh báo đòn bẩy tài chính (loại trừ ngân hàng khỏi công thức đòn bẩy phi tài chính).
- **Bộ nút tác vụ nhanh:** Nút `Chart {Ticker}` mở TradingView; Nút `Tra cứu SEC ↗`; Nút `Chi tiết {Ticker} 🔍` mở hộp thoại phân tích setup.

#### Thanh công cụ lọc & Chuyển đổi giao diện:
- Ô tìm kiếm mã hoặc tên công ty theo thời gian thực.
- Hộp kiểm `Chỉ xem Leader ⭐`: Lọc nhanh các cổ phiếu đầu đàn.
- Chuyển đổi chế độ: `Thẻ Chi Tiết` (Bento Cards) hoặc `Bảng Rút Gọn` (Interactive Table có thể click sắp xếp theo cột Giá, Trigger, 1D, 1W, 1M, ATR, Score).
- Bộ lọc `Chu kỳ tuần`: Cho phép lọc ẩn các mã khi tuần chỉ còn $\le 1$ phiên giao dịch, giúp loại bỏ rủi ro mở vị thế mới bị ôm qua kỳ nghỉ cuối tuần (`crosses_weekend`).
- Nút `Xuất CSV 📥`: Tải danh sách ứng viên đang hiển thị ra file CSV.

---

### 2.3 Bảng So Sánh Trực Diện 2–5 Ứng Viên (Side-by-Side Comparison)
Nằm trong khối mở rộng `⚖️ So sánh Trực diện 2–5 Ứng viên`, tính năng này giải quyết bài toán lựa chọn khi có nhiều cổ phiếu cùng phát tín hiệu:
- Chọn từ 2 đến 5 mã cổ phiếu bất kỳ trong danh sách ứng viên.
- Hiển thị bảng so sánh đa cột song song trực quan:
  - So sánh trực tiếp Giá, Mức Trigger, Mức Dừng Lỗ (Invalidation).
  - Tỷ lệ phần trăm rủi ro cắt lỗ ước tính (`Risk Stop % = (Trigger - Invalidation) / Trigger`).
  - So sánh điểm số (`Score`), biến động (`ATR%`), hiệu suất 1D/1W/1M.
  - Đối chiếu Hồ sơ áp lực mua/bán đa phiên (Buying/Selling Pressure Bias).
  - Đối chiếu các chỉ số tăng trưởng Doanh thu, EPS và ngày ra BCTC sắp tới.

---

### 2.4 Góc nhìn 03: Phân Hệ Lịch Báo Cáo Tài Chính (Earnings Calendar)
Mùa công bố kết quả kinh doanh là nguồn gốc của các cú nhảy giá (gap) $10\% - 20\%$ qua đêm có thể phá hủy tài khoản swing trade. Phân hệ Lịch BCTC toàn diện giúp quản trị triệt để rủi ro này:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ BỘ LỌC LỊCH BÁO CÁO TÀI CHÍNH:                                         │
│ Khung thời gian: [Tuần Này] [Tuần Tới] [14 Ngày Tới] [Tùy Chọn...]      │
│ Phạm vi:         [Tất cả S&P 500] [Chỉ Ứng Viên Radar]                 │
│ Thời điểm:       [Tất cả] [☀️ BMO - Trước giờ mở] [🌙 AMC - Sau giờ đóng]│
│ Chế độ xem:      [📅 Lịch Tuần (Grid)]  [📋 Bảng Chi Tiết]             │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Chế độ Lịch Tuần (Weekly Schedule Grid):**
   - Phân chia thành 5 cột từ Thứ Hai đến Thứ Sáu.
   - Trong mỗi ngày, tách biệt thành 2 khoang rõ ràng:
     - `☀️ TRƯỚC GIỜ MỞ CỬA (BMO - Before Market Open)`: Doanh nghiệp báo cáo trước 09:30 ET; giá sẽ phản ứng ngay khi phiên mở cửa.
     - `🌙 SAU GIỜ ĐÓNG CỬA (AMC - After Market Close)`: Doanh nghiệp báo cáo sau 16:00 ET; giá phản ứng trong phiên After-hours và nến mở cửa ngày hôm sau.
   - Mỗi mã cổ phiếu hiển thị dạng thẻ bento nhỏ gồm: Mã, Tên công ty, Vốn hóa, Ngành, nhãn `RADAR CANDIDATE` (nổi bật nếu là ứng viên đang có setup), cùng link mở TradingView và SEC EDGAR.
2. **Chế độ Bảng Chi Tiết (Full Interactive Table):**
   - Hiển thị danh sách dạng bảng dữ liệu: Ngày báo cáo, Thời điểm (BMO/AMC/TBD), Mã, Công ty, Vốn hóa, Ngành, Doanh thu ước tính, EPS ước tính, Cột kiểm tra có nằm trong danh sách Radar hay không, và liên kết tra cứu.

---

### 2.5 Hộp Thoại Chi Tiết Setup (Setup Detail Dialog — 3 Tabs Nội Bộ)
Khi click nút `Chi tiết setup 🔍`, hệ thống mở một modal phân tích chuyên sâu được tổ chức thành 3 tab nội bộ khoa học, loại bỏ hoàn toàn tình trạng cuộn trang mệt mỏi:

#### Khối Thông Tin Đầu Trang (Executive Context Bar):
- Ticker, Tên công ty, Ngành GICS, Nhóm chiến thuật, Nút mở TradingView toàn màn hình.
- 4 Thẻ chỉ số tổng quan:
  - `Giá & Điểm số`: Giá chốt phiên, Điểm số kỹ thuật, Thứ hạng trong ngày.
  - `Biến động (ATR14)`: Giá trị biến động tuyệt đối (\$), Tỷ lệ ATR% so với thị giá, Đánh giá độ biến động (Thấp / Vừa phải / Cao).
  - `Thanh khoản & Giá trị GD`: Khối lượng bình quân 20 phiên, Giá trị giao dịch khớp lệnh trung bình ngày (Dollar Volume tính bằng Triệu/Tỷ USD), Tỷ lệ Relative Volume (RVOL) phiên gần nhất.
  - `Bối cảnh Khung Tuần (W1)`: Xu hướng tuần (Tăng / Giảm / Đi ngang), kèm huy hiệu **`Đã đóng tuần`** (nếu là nến Thứ Sáu chốt tuần) hoặc **`Tuần chưa đóng (Tạm thời)`** (nếu đang giữa tuần, tránh lấy tín hiệu tuần chưa hoàn thiện làm căn cứ tuyệt đối).

#### Tab 1: 📈 Kỹ Thuật & Mức Giá
- **Biểu đồ Kỹ thuật Point-in-Time:**
  - Biểu đồ nến OHLC kết hợp đường MA20 (Xanh dương), MA50 (Cam), MA200 (Xám đứt).
  - **Tuyệt đối không rò rỉ dữ liệu tương lai:** Biểu đồ chỉ vẽ nến lịch sử tính đến đúng ngày `as_of` của snapshot.
  - 4 Đường ngang mức giá kỹ thuật được vẽ trực tiếp lên biểu đồ:
    - Đường nét đứt màu xanh lá: **Mức Kích Hoạt (Trigger)**.
    - Đường chấm màu đỏ: **Mức Vô Hiệu Hóa / Dừng Lỗ (Invalidation)**.
    - Đường chấm màu xanh dương nhạt: **Hỗ Trợ Tham Chiếu (Support)**.
    - Đường chấm màu cam nhạt: **Kháng Cự Tham Chiếu (Resistance)**.
  - Khoang phụ bên dưới hiển thị Khối lượng giao dịch kèm đường trung bình khối lượng 20 phiên.
- **Bảng Mức Tham Chiếu Phân Tích (Technical Reference Levels):**
  - Trình bày 5 hàng chuẩn hóa: Giá Đóng Cửa, Mức Kích Hoạt, Mức Vô Hiệu Hóa, Hỗ Trợ, Kháng Cự, Đường MA20.
  - Cung cấp chính xác: Mức giá (\$); Khoảng cách chênh lệch so với giá đóng cửa theo tỷ lệ phần trăm (`%`); Khoảng cách quy đổi theo **bội số ATR** (ví dụ: cách MA20 `+0.45 ATR`); và **Phương pháp & Căn cứ xác định khách quan** (ví dụ: *Đỉnh 20 phiên trước*, *Đáy nến thấp nhất 3 phiên gần nhất*, *Đường trung bình MA50*).
  - Nút bấm `Xuất mức kỹ thuật (CSV cho Excel)`: Tải bảng số liệu để dán trực tiếp vào bảng tính quản lý lệnh cá nhân.

#### Tab 2: 🕯️ Nến Nhật & Bối Cảnh FA
- **Nhận Diện Nến Gần Nhất & Phản Ứng Giá (2 Lớp Phân Tích Khách Quan):**
  - *Lớp 1 — Hình học nến định lượng:* Tỷ lệ thân nến trên tổng biên độ (`body_ratio`), tỷ lệ râu trên (`upper_shadow`), râu dưới (`lower_shadow`), vị trí mức đóng cửa (`close_position_pct`), biên độ phiên so với ATR14 (`range_to_atr`).
  - *Lớp 2 — Mẫu hình & Bối cảnh:* Nhận diện Doji, Marubozu, Hammer (Râu dưới dài), Shooting Star (Râu trên dài), Bullish/Bearish Engulfing, Inside Bar, Outside Bar.
  - *Thông dịch bối cảnh 3 dòng:* Tóm tắt nến gần nhất $\rightarrow$ Đặt vào vị trí xu hướng hiện tại $\rightarrow$ Đánh giá trạng thái phản ứng (`Đạt / Thuận lợi`, `Cần thận trọng`, hoặc `Xấu`). *Ví dụ: Hammer xuất hiện tại hỗ trợ MA20 trong nhịp pullback xác nhận hỗ trợ; nhưng nếu xuất hiện sau khi giá đã tăng vượt xa MA20 $>1.5$ ATR thì là tín hiệu rủi ro mua đuổi.*
- **Hồ Sơ Áp Lực Mua/Bán Đa Phiên (Multi-Session Pressure Profile):**
  - Thay thế cách diễn giải cảm tính ("lái gom hàng", "dòng tiền lớn") bằng các bằng chứng quan sát giá-khối lượng thực tế qua 1, 3 và 5 phiên.
  - Bảng thống kê chi tiết từng phiên: Ngày, Giá đóng cửa, Lợi suất 1D, Tỷ lệ RVOL so với trung vị 20 phiên, Vị trí đóng cửa trong phiên, Biên độ nến / ATR14.
  - Phân tách thành 3 khối bằng chứng: `🟢 BẰNG CHỨNG HỖ TRỢ` (ví dụ: Phiên tăng kèm RVOL cao, đóng cửa sát đỉnh phiên), `🔴 BẰNG CHỨNG TRÁI CHIỀU` (ví dụ: Xuất hiện râu trên dài khi chạm kháng cự), và `⚪ KHOẢNG TRỐNG / TRUNG TÍNH`.
- **Bối Cảnh Doanh Nghiệp & Lịch Công Bố BCTC (Fundamental Context):**
  - Thẻ thông tin xuất xứ dữ liệu minh bạch: Kỳ báo cáo kết thúc gần nhất (MRQ/FY), Loại kỳ so sánh (Quarterly YoY), Đồng tiền (USD), Nguồn cấp (Yahoo Finance Số liệu tổng hợp), Thời điểm thu thập dữ liệu.
  - 4 Thẻ chỉ số tài chính cơ bản: Doanh thu YoY, EPS YoY, Biên lợi nhuận ròng, Kỳ BCTC tiếp theo.
  - Danh sách Cờ cảnh báo tài chính: Cảnh báo nợ vay/đòn bẩy cao, Cảnh báo biên lợi nhuận âm, Cảnh báo ngày ra tin BCTC sát nút, Ghi chú định chế tài chính/ngân hàng.
  - Nút mở `Tra cứu hồ sơ BCTC trên SEC EDGAR ↗`.

#### Tab 3: ✅ Checklist & Điều Kiện
- **Bảng Checklist Kiểm Định Quy Tắc (Pass / Fail / N/A):**
  - Đối chiếu từng tiêu chí định lượng của hệ thống đối với cổ phiếu được chọn.
  - Huy hiệu trạng thái trực quan:
    - `ĐẠT / PASS` (Xanh lá): Cổ phiếu thỏa mãn trọn vẹn tiêu chí.
    - `CHƯA ĐẠT / FAIL` (Đỏ): Tiêu chí bị vi phạm (ví dụ: Khối lượng chưa đạt 1.5x bình quân).
    - `THIẾU DỮ LIỆU / N/A` (Vàng): Không đủ dữ liệu lịch sử để đánh giá (ví dụ: Mã mới niêm yết chưa đủ 200 nến để tính MA200).
- Khối cảnh báo rủi ro đặc thù và nút mở TradingView toàn màn hình.

---

## 3. TRỤ CỘT 2: 🌐 BẢN ĐỒ THỊ TRƯỜNG & NGÀNH

Trụ cột phân tích Top-Down giúp trả lời 2 câu hỏi lớn: *"Thị trường chung đang ở chế độ Chấp nhận Rủi ro (Risk-On) hay Phòng thủ (Risk-Off)?"* và *"Dòng tiền đang luân chuyển vào nhóm ngành nào?"*.

---

### 3.1 Góc nhìn 01: Bức Tranh Thị Trường & Độ Rộng Tham Gia
Cung cấp góc nhìn toàn cảnh về nội lực thực sự của thị trường chứng khoán Mỹ, vượt qua lớp vỏ bọc điểm số của chỉ số vốn hóa.

### 3.2 Cụm Biểu Đồ Nến 3 Chỉ Số Lớn (S&P 500, NASDAQ, DOW)
Được thiết kế đồng bộ theo chuẩn Light Theme sắc nét:
- 3 Thẻ biểu đồ nến độc lập cho:
  1. **S&P 500 Index (`SPY` / `^GSPC`)**
  2. **NASDAQ 100 (`QQQ` / `^IXIC`)**
  3. **Dow Jones Industrial Average (`DIA` / `^DJI`)**
- **Đặc điểm hiển thị:**
  - Nền trắng tinh gọn `#FFFFFF`, viền bo góc `#EAEAEA`.
  - Huy hiệu giá đóng cửa màu vàng hổ phách nhạt thanh lịch (`#FEF08A` chữ `#854D0E`).
  - Đường tham chiếu ngang màu đỏ chấm biểu thị mức giá đóng cửa phiên trước (`Prev Close`).
  - Các cột Relative Volume màu xanh hoàng gia (`#2563EB`) bên dưới đồ thị.
  - Nút chuyển đổi khung thời gian linh hoạt: `Nến 5m trong ngày (Intraday)` để theo dõi diễn biến phiên hiện tại, hoặc `Nến ngày (30 phiên gần nhất)` để nắm bắt cấu trúc swing ngắn hạn.

---

### 3.3 5 Thanh Bar Đối Chiếu Tỷ Lệ Độ Rộng Thị Trường
Thay vì chỉ hiển thị các con số khô khan, hệ thống sử dụng **5 Thanh Bar Đối Chiếu Hai Chiều (Bi-color Contrast Bars)** trực quan, phân tách giữa phe Mua (Xanh lá `#16A34A`) và phe Bán (Đỏ `#DC2626`):

```text
1. Mã Tăng vs Giảm (Advancing vs Declining):
   [████████████████████████ 68% | 32% ██████████]  (342 mã Tăng / 161 mã Giảm)

2. Đỉnh 20 Phiên vs Đáy 20 Phiên (New Highs vs New Lows):
   [██████████████████████████████ 85% | 15% ████]  (45 đỉnh mới / 8 đáy mới)

3. Cổ phiếu Trên vs Dưới Đường Trung Hạn SMA50:
   [██████████████████ 55% | 45% ███████████████]  (277 trên / 226 dưới)

4. Cổ phiếu Trên vs Dưới Đường Cấu Trúc Dài Hạn SMA200:
   [██████████████████████ 62% | 38% ███████████]  (312 trên / 191 dưới)

5. Xung Lực Ngắn Hạn (Bullish vs Bearish Momentum):
   [████████████████████ 58% | 42% █████████████]  (Tổng hợp động lượng)
```

> **Cách đọc nhanh độ rộng thị trường:**
> - **Thị trường Khỏe (Healthy Bull):** Khi cả 5 thanh bar đều có tỷ lệ phe Xanh áp đảo $>60\%$. Đặc biệt, tỷ lệ New Highs phải vượt trội New Lows.
> - **Thị trường Phân Kỳ Cảnh Báo (Divergence Warning):** Điểm số S&P 500 tăng nhưng thanh bar SMA50 hoặc A/D lại có phe Đỏ chiếm $>50\%$.

---

### 3.4 Phân Kỳ Vốn Hóa (SPY vs RSP) & Chuỗi Thời Gian Độ Rộng
1. **Đối chiếu SPY (Cap-Weighted) vs RSP (Equal-Weighted):**
   - So sánh trực diện hiệu suất giữa chỉ số theo vốn hóa (bị chi phối nặng bởi nhóm "Magnificent 7") và chỉ số bình quân (mỗi cổ phiếu có trọng số ngang nhau $0.2\%$).
   - **Tín hiệu lan tỏa lành mạnh:** Cả SPY và RSP đều tăng với biên độ tương đương $\rightarrow$ Dòng tiền tham gia diện rộng, an toàn cho swing trading.
   - **Tín hiệu phân kỳ co cụm (Mega-Cap Masking):** SPY tăng mạnh nhưng RSP đi ngang hoặc giảm $\rightarrow$ Điểm số bị "kéo ảo" bởi một vài cổ phiếu vốn hóa khổng lồ trong khi đa số cổ phiếu trên sàn đang suy yếu.
2. **Các đường biểu đồ chuỗi thời gian phân tích độ rộng:**
   - **Đường A/D Tích Lũy (Cumulative Advance/Decline Line):** Đo lường xu hướng tích lũy dòng tiền toàn thị trường.
   - **Đường AD Volume Line:** So sánh tỷ trọng khối lượng của các mã tăng so với các mã giảm.
   - **Lịch sử tỷ lệ % Cổ phiếu trên MA20, MA50, MA200:** Biểu đồ đường thể hiện sự cải thiện hoặc suy yếu của độ rộng qua thời gian. *Đặc biệt: Hệ thống tự động loại trừ các mã thiếu dữ liệu khỏi mẫu số quan sát để đảm bảo tỷ lệ phần trăm không bị méo mó.*
   - **Chênh lệch Lợi suất Bình quân (Equal-Weight) vs Trung vị (Median Return):** Đo lường mức độ ảnh hưởng của các mã ngoại lai (outliers) lên thị trường.

---

### 3.5 Góc nhìn 02: 11 Ngành GICS (Sector Rotation & Health)
Phân tích chi tiết 11 nhóm ngành kinh tế chính thức của thị trường chứng khoán Mỹ thông qua 11 quỹ ETF đại diện của SPDR:

| Ticker ETF | Tên Ngành GICS (Tiếng Việt) | Nhóm Cổ Phiếu Tiêu Biểu |
|---|---|---|
| **XLK** | Công nghệ Thông tin (Technology) | Apple, Microsoft, NVIDIA, Broadcom |
| **XLF** | Tài chính (Financials) | JPMorgan Chase, Berkshire Hathaway, Visa |
| **XLV** | Y tế & Chăm sóc Sức khỏe (Health Care) | Eli Lilly, UnitedHealth, Johnson & Johnson |
| **XLY** | Tiêu dùng Không thiết yếu (Consumer Discretionary) | Amazon, Tesla, Home Depot |
| **XLC** | Dịch vụ Giao tiếp (Communication Services) | Alphabet (Google), Meta, Netflix |
| **XLI** | Công nghiệp (Industrials) | Caterpillar, GE Aerospace, Union Pacific |
| **XLP** | Tiêu dùng Thiết yếu (Consumer Staples) | Procter & Gamble, Costco, Walmart |
| **XLE** | Năng lượng (Energy) | ExxonMobil, Chevron, ConocoPhillips |
| **XLU** | Tiện ích Công cộng (Utilities) | NextEra Energy, Southern Company, Duke Energy |
| **XLRE**| Bất động sản (Real Estate) | Prologis, American Tower, Equinix |
| **XLB** | Vật liệu Cơ bản (Materials) | Linde, Sherwin-Williams, Freeport-McMoRan |

---

### 3.6 Biểu Đồ Luân Chuyển 4 Góc Phần Tư RRG & Vệt Lịch Sử 10 Phiên
Hệ thống sử dụng biểu đồ phân tán 4 góc phần tư mô phỏng mô hình **Relative Rotation Graph (RRG)** để theo dõi quỹ đạo dịch chuyển dòng tiền:

```text
                 Y: Động Lượng Xoay Trục (Momentum Change)
                               ▲
           CẢI THIỆN           │           DẪN DẮT
          (IMPROVING)          │          (LEADING)
          Màu Xanh Dương       │         Màu Xanh Lá
                               │
   ◄───────────────────────────┼───────────────────────────► X: Sức Mạnh Tương Đối
                               │                                (Relative Strength)
           TỤT HẬU             │           SUY YẾU
          (LAGGING)            │         (WEAKENING)
          Màu Đỏ               │          Màu Vàng
                               ▼
```

- **Công thức tọa độ toán học:**
  - Trục hoành: $X = 100 \times \left( \frac{R}{\text{EMA}_{20}(R)} - 1 \right)$, trong đó $R = \frac{\text{Giá ETF}}{\text{Giá SPY}}$. Đo lường sức mạnh tương đối của ngành so với thị trường chung.
  - Trục tung: $Y = X_t - X_{t-5}$. Đo lường gia tốc (tốc độ thay đổi động lượng) trong 5 phiên gần nhất.
- **Vệt Lịch Sử 10 Phiên (10-Session Historical Trail):** Mỗi ngành được vẽ một vệt mũi tên thể hiện quỹ đạo di chuyển qua 10 phiên giao dịch gần nhất tại mốc thời gian `as_of`. Giúp nhà giao dịch nhìn rõ ngành đang xoay theo chiều kim đồng hồ: từ *Improving $\rightarrow$ Leading $\rightarrow$ Weakening $\rightarrow$ Lagging*.

---

### 3.7 Đánh Giá Sức Khỏe Nội Bộ Ngành & Cảnh Báo Mega-Cap Masking
Hệ thống tách bạch rạch ròi giữa **Luân chuyển tương đối của ETF ngành** và **Sức khỏe thực chất bên trong ngành**:
- **Tỷ lệ % mã trên SMA50 và SMA200 nội bộ ngành:** Đánh giá xem đà tăng của ETF ngành có được sự đồng thuận của đa số cổ phiếu thành viên hay không.
- **Phát hiện Méo mó Vốn hóa (Mega-Cap Masking Alert):** Nếu ETF ngành (ví dụ XLK) tăng mạnh nhưng tỷ lệ mã thành viên tăng giá lại giảm sút $\rightarrow$ Hệ thống lập tức hiển thị cảnh báo phân kỳ nội bộ, cảnh báo rủi ro khi mua các mã công nghệ vốn hóa vừa/nhỏ theo đà ETF.
- **Ước tính Thanh khoản (`turnover_est`) & Mức độ Tập trung Top 5:** Tính toán tổng giá trị giao dịch ước tính của ngành và tỷ trọng vốn hóa của 5 mã lớn nhất, giúp nhận diện dòng tiền tổ chức đang tập trung vào đâu.
- **Drill-down Nhóm Ngành Con (Sub-Industries Drill-down):** Khi click vào một ngành, bảng dữ liệu mở rộng chi tiết toàn bộ các phân ngành con, số mã thành viên, lợi suất bình quân và cổ phiếu dẫn đầu.

---

### 3.8 Góc nhìn 03: Ma Trận 127 Nhóm Ngành O'Neil (CANSLIM Percentile Matrix)
Khai thác triết lý đầu tư huyền thoại của William O'Neil: *"Cổ phiếu chiến thắng lớn nhất luôn xuất phát từ các nhóm ngành dẫn dắt hàng đầu"*.

1. **Phân loại 127 Phân Ngành GICS (Sub-Industries):**
   - Đánh giá hiệu suất đa khung thời gian: 1 Ngày, 1 Tuần, 1 Tháng, 3 Tháng, 6 Tháng, 1 Năm.
   - Chuẩn hóa thứ hạng thành điểm bách phân **Percentile 1 – 99** (99 là mạnh nhất, 1 là yếu nhất).
2. **Hai Điểm Số Xếp Hạng Độc Quyền:**
   - **Điểm COMP (Composite Score):** Điểm tổng hợp cân bằng sức mạnh trên toàn bộ các khung thời gian từ 1 tuần đến 1 năm.
   - **Điểm BLEND:** Kết hợp tỷ trọng giữa xung lực bứt phá ngắn hạn (1D, 1W) và nền tảng xu hướng trung hạn (1M, 3M).
3. **Chế Độ Xem Kép (Dual Heatmap Modes):**
   - `Chế độ COMP / BLEND`: Bản đồ nhiệt hiển thị thứ hạng bách phân từ 1 đến 99 với thang màu chuyển dịch từ đỏ (yếu) sang xanh lá đậm (dẫn dắt).
   - `Chế độ Độ Rộng & Lợi Suất Trung Vị`: Hiển thị tỷ lệ mã trên MA50 và mức lợi suất trung vị của từng phân ngành nhỏ.
4. **Interactive Stock Pills (Thẻ Cổ Phiếu Nhanh):**
   - Trong mỗi ô ngành, hệ thống hiển thị trực tiếp danh sách các cổ phiếu đầu đàn dạng viên thuốc (pills).
   - Màu sắc xanh/đỏ phản ánh hiệu suất trong phiên của từng mã.
   - Click trực tiếp vào pill để mở biểu đồ TradingView của mã đó ngay lập tức.
5. **Cờ hiệu `⭐ O'Neil Leader` trên Radar:**
   - Bất kỳ cổ phiếu nào đạt tiêu chuẩn kỹ thuật swing VÀ đồng thời thuộc **Top 20% nhóm ngành mạnh nhất** (COMP $\ge 80$) sẽ được hệ thống tự động gắn cờ `⭐ O'Neil Leader` và cộng điểm ưu tiên `Score`, giúp nhà giao dịch tập trung tối đa nguồn vốn vào nhóm dẫn dắt thị trường.

---

## 4. TRỤ CỘT 3: 📊 ĐO LƯỜNG & KIỂM TOÁN

Trụ cột khoa học đảm bảo tính khách quan và minh bạch tuyệt đối, loại bỏ sự "tự huyễn hoặc" về hiệu quả của các quy tắc kỹ thuật.

---

### 4.1 Góc nhìn 01: Hiệu Quả Tín Hiệu (Alpha Audit & Forward Outcomes)
Không giống như các phần mềm thương mại thường chỉ đưa ra khuyến nghị mà không bao giờ đo lường lại, Market Radar tích hợp sẵn một hệ thống **Kiểm toán Thống kê Tín hiệu Độc lập**:

```text
Tín hiệu xuất hiện (EOD Snapshot) ──> Ghi nhận giá MỞ CỬA phiên sau (Next Open)
                                              │
         ┌────────────────────────────────────┴────────────────────────────────────┐
         ▼                                                                         ▼
[Đo Lường Chu Kỳ Giữ Lệnh Đa Phiên]                       [Đo Lường Rủi Ro Dao Động Giá]
- Forward Return: 5D, 10D, 20D                             - MFE: Maximum Favorable Excursion
- Swing Trong Tuần: 1D, 2D, 3D, 4D, Week-Close 99         - MAE: Maximum Adverse Excursion
- Alpha vs SPY Benchmark                                  - Quy đổi theo % và Bội số ATR
```

1. **Loại bỏ Hoàn Toàn Thiên Kiến Nhìn Thấy Trước (Look-Ahead Bias):**
   - Khi bộ lọc phát hiện setup vào lúc kết thúc phiên $T$, giá vào lệnh giả định **không phải là giá đóng cửa phiên $T$**, mà được ghi nhận chính xác tại **Giá Mở Cửa (Open) của phiên $T+1$**.
2. **Theo Dõi Đợt Tín Hiệu (Signal Streaks):**
   - Hệ thống tự động gom các tín hiệu xuất hiện liên tiếp của cùng một cổ phiếu thành một đợt duy nhất (`Streak`), tránh tình trạng một mã tăng mạnh được tính lặp lại nhiều lần làm sai lệch kết quả thống kê.
3. **Các Chỉ Số Hiệu Quả Cốt Lõi:**
   - `Tỷ lệ Thắng (Win Rate)`: Tỷ lệ phần trăm các tín hiệu đạt lợi nhuận dương sau $N$ phiên.
   - `Lợi Nhuận Bình Quân & Trung Vị (Mean / Median Return)`: Đo lường mức sinh lời kỳ vọng.
   - `Alpha so với SPY`: Hiệu suất chênh lệch so với chỉ số chuẩn SPY trong cùng kỳ hạn. *Chỉ khi Alpha $>0$, bộ lọc mới thực sự tạo ra giá trị vượt trội so với việc nắm giữ thụ động chỉ số.*
   - `MFE (Maximum Favorable Excursion)`: Mức lãi tiềm năng tối đa mà giá đạt được trong suốt thời gian giữ lệnh (tính theo % và bội số ATR). Cho biết setup có mở ra dư địa chạy sóng tốt hay không.
   - `MAE (Maximum Adverse Excursion)`: Mức lỗ tối đa mà vị thế phải chịu đựng trước khi đạt mục tiêu (tính theo % và bội số ATR). Giúp xác định mức đặt Stop Loss tối ưu.
4. **Cảnh Báo Gross Return vs P&L Thực Tế:**
   - Hệ thống luôn hiển thị thông báo lưu ý: *Kết quả kiểm toán là Lợi nhuận gộp danh nghĩa (Gross Return), chưa tính chi phí trượt giá (slippage), phí hoa hồng broker và lãi vay margin / phí mượn cổ phiếu short.*

---

### 4.2 Đo Lường Swing Trong Tuần (In-Week Swing & Week-Close 99)
Dành riêng cho phong cách giao dịch swing ngắn dứt điểm trong tuần, không ôm lệnh qua ngày nghỉ Thứ Bảy / Chủ Nhật:
- Đo lường hiệu suất riêng biệt cho các chu kỳ nắm giữ: **1 phiên (1D), 2 phiên (2D), 3 phiên (3D), 4 phiên (4D)**.
- **Kỳ hạn Chốt Cuối Tuần (`Week-Close 99`):** Giả định vị thế được mở trong tuần và bắt buộc đóng tại giá Close của phiên Thứ Sáu.
- Tự động gắn nhãn `no_window_in_week` cho các tín hiệu xuất hiện vào Thứ Năm hoặc Thứ Sáu khi thời gian không còn đủ cho một chu kỳ swing hoàn chỉnh.
- **Phân rã Ma Trận theo Thứ & Chiều Giao Dịch:** Bảng thống kê tỷ lệ thắng và lợi suất theo từng ngày trong tuần (Thứ Hai $\rightarrow$ Thứ Sáu) kết hợp với chiều Long / Short, giúp nhận diện ngày nào trong tuần vào lệnh có xác suất thắng cao nhất.

---

### 4.3 Khảo Sát Lợi Thế Nến Nhật (Candlestick Edge Audit)
Kiểm tra xem mẫu nến Nhật xuất hiện tại phiên phát tín hiệu có thực sự đóng góp vào tỷ lệ thắng hay không:
- Thống kê độc lập số lượng mẫu, tỷ lệ thắng, lợi suất bình quân và Alpha của từng mẫu nến cụ thể: *Doji, Thân dài (Marubozu), Râu dưới dài (Hammer), Râu trên dài (Shooting Star), Nhấn chìm tăng (Bullish Engulfing), Inside Bar, Outside Bar*.
- Giúp người dùng loại bỏ các mẫu nến có vẻ đẹp mắt nhưng thống kê thực tế lại đem lại kết quả âm.

---

### 4.4 Kiểm Định Tính Đơn Điệu Của Score (Top vs Bottom Quartile)
Để chứng minh thuật toán tính điểm `Score` của Market Radar có ý nghĩa thống kê thực sự:
- Hệ thống chia toàn bộ tín hiệu thành 4 nhóm tứ phân vị dựa trên điểm số: Nhóm 25% điểm cao nhất (`Top Quartile - Q1`) đến Nhóm 25% điểm thấp nhất (`Bottom Quartile - Q4`).
- **Nguyên lý kiểm định đơn điệu (Monotonicity Test):** Nếu thuật toán hoạt động chuẩn xác, nhóm Q1 bắt buộc phải có tỷ lệ thắng và Alpha cao hơn rõ rệt so với nhóm Q4. Nếu kết quả ngẫu nhiên hoặc Q4 cao hơn Q1, hệ thống sẽ cảnh báo thuật toán tính điểm cần được hiệu chỉnh lại trọng số.

---

### 4.5 Góc nhìn 02: So Sánh Biến Động Snapshot (Delta History)
Công cụ đối chiếu sự dịch chuyển giữa 2 thời điểm bất kỳ (mặc định giữa snapshot hiện tại và snapshot liền trước):
- **3 Chỉ số Delta:** Số lượng mã mới xuất hiện trong danh sách (`Added`), số lượng mã bị loại khỏi danh sách (`Removed`), và số lượng mã tiếp tục duy trì (`Retained`).
- **Bảng Cổ Phiếu Mới Xuất Hiện:** Danh sách các mã mới kèm nhóm setup và thị giá.
- **Bảng Cổ Phiếu Rời Danh Sách:** Nhận diện các mã bị mất điều kiện kỹ thuật để kịp thời đóng lệnh hoặc hạ tỷ trọng.
- **Bảng Biến Động Thứ Hạng Ngành:** Theo dõi thứ hạng 11 ngành GICS tăng hay giảm bao nhiêu bậc (ví dụ: `XLK: Hạng cũ #4 -> Hạng mới #1 (+3)`).

---

### 4.6 Góc nhìn 03: Giám Sát Chất Lượng Dữ Liệu & Nguyên Tắc 0 Đồng
Báo cáo kỹ thuật chi tiết về tính toàn vẹn của dữ liệu:
- **Kiểm toán độ bao phủ:** Số lượng mã trong tổng số 503 mã có dữ liệu hợp lệ; tỷ lệ bao phủ đồng phiên (ngưỡng an toàn $\ge 95\%$); tỷ lệ mã có đủ lịch sử 253 phiên giao dịch (1 năm).
- **Danh sách mã lỗi:** Liệt kê công khai các ticker bị lỗi kết nối hoặc thiếu nến lịch sử để người dùng nắm rõ.
- **4 Nguyên Tắc Vận Hành Bất Biến:**
  1. *Chi phí dữ liệu 0 đồng:* Khai thác 100% nguồn dữ liệu công khai chất lượng cao (Wikipedia và Yahoo Finance).
  2. *Xử lý ngoại lệ chuẩn mực:* Không gán giá trị 0 giả tạo cho mã thiếu dữ liệu; mã không đủ chuẩn sẽ bị loại khỏi mẫu số tính toán.
  3. *Ngoại lệ Định chế Tài chính & Ngân hàng:* Cơ cấu tài sản của ngân hàng được phân loại riêng, không áp dụng máy móc chỉ số nợ/vốn chủ hay dòng tiền của doanh nghiệp sản xuất.
  4. *Cảnh báo Bán Khống (Short):* Luôn yêu cầu người dùng kiểm tra khả năng mượn cổ phiếu (`Hard-to-borrow`) và phí vay tại sàn giao dịch cá nhân.
- **Khóa Tiến Trình Hệ Điều Hành (`ProcessLock`):** Cơ chế khóa file độc quyền ngăn chặn triệt để tình trạng hai tiến trình cập nhật chạy đè lên nhau gây hỏng cơ sở dữ liệu SQLite.

---

## 5. TÍCH HỢP NGOÀI & XUẤT DỮ LIỆU

Market Radar được thiết kế theo tư duy **Mở & Kết Nối Liền Mạch** với các công cụ chuyên nghiệp của trader.

### 5.1 Tích hợp biểu đồ TradingView 1-Click
- Mọi thẻ cổ phiếu, bảng dữ liệu, hàng sự kiện và ô heatmap O'Neil đều có nút bấm hoặc liên kết trực tiếp mở TradingView.
- Định dạng link chuẩn hóa: `https://www.tradingview.com/chart/?symbol={TICKER}&interval=D`.
- Tự động mở đúng biểu đồ nến ngày (D1) của cổ phiếu trên tab mới của trình duyệt chỉ với 1 cú click chuột, loại bỏ hoàn toàn thao tác gõ lại từng mã thủ công.

### 5.2 Tra cứu hồ sơ pháp lý SEC EDGAR 1-Click
- Tích hợp trực tiếp với cổng thông tin điện tử của Ủy ban Giao dịch và Chứng khoán Hoa Kỳ (U.S. Securities and Exchange Commission).
- Liên kết tự động theo CIK hoặc Ticker: `https://www.sec.gov/edgar/browse/?CIK={TICKER}`.
- Giúp nhà giao dịch kiểm tra ngay các báo cáo tài chính quý 10-Q, báo cáo năm 10-K, giao dịch nội bộ Form 4 và các sự kiện bất thường 8-K chính thức từ cơ quan quản lý trước khi mạo hiểm dòng vốn.

### 5.3 Xuất file CSV phục vụ Nhật ký Giao dịch (Trading Journal / Excel)
Hệ thống cung cấp 3 cấp độ xuất dữ liệu CSV định dạng chuẩn quốc tế:
1. **Xuất toàn bộ Ứng viên (Sidebar Export):** Xuất toàn bộ danh sách cổ phiếu đạt chuẩn của snapshot.
2. **Xuất Ứng viên theo Bộ lọc (In-Tab Export):** Xuất danh sách đã qua chọn lọc theo nhóm hoặc ngành.
3. **Xuất Mức Kỹ thuật Setup (Setup Level Export):** Nằm trong tab 1 của Modal chi tiết setup, xuất đầy đủ 5 mức giá kỹ thuật kèm phương pháp căn cứ để dán trực tiếp vào file Excel quản lý danh mục cá nhân.
