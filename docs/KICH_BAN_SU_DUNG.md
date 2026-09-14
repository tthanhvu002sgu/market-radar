# MARKET RADAR — HƯỚNG DẪN THEO KỊCH BẢN SỬ DỤNG
## CẨM NANG VẬN HÀNH & KỊCH BẢN GIAO DỊCH THỰC CHIẾN (PRACTICAL PLAYBOOK)

---

> **Tên hệ thống:** Market Radar — S&P 500 Top-Down Swing Trading Radar  
> **Dành cho:** Nhà giao dịch Swing Trading (Retail & Systematic Traders) trên thị trường cổ phiếu Mỹ  
> **Mục tiêu:** Cung cấp hướng dẫn quy trình từng bước (Step-by-step Standard Operating Procedures) từ khâu quét thị trường, chọn lọc ngành, sàng lọc mã đến thực thi lệnh trên sàn giao dịch nhằm tối đa hóa tỷ lệ thắng và kiểm soát rủi ro vốn.

---

## MỤC LỤC

1. [TRIẾT LÝ VẬN HÀNH & NGUYÊN TẮC BẢO VỆ VỐN](#1-triết-lý-vận-hành--nguyên-tắc-bảo-vệ-vốn)
2. [KỊCH BẢN 1: QUY TRÌNH CHUẨN BỊ HÀNG NGÀY TRƯỚC PHIÊN MỞ CỬA (PRE-MARKET ROUTINE — 15 PHÚT)](#2-kịch-bản-1-quy-trình-chuẩn-bị-hàng-ngày-trước-phiên-mở-cửa-pre-market-routine--15-phút)
3. [KỊCH BẢN 2: SĂN CƠ HỘI ĐÓN SÓNG DẪN DẮT / ĐỘT PHÁ (MOMENTUM & BREAKOUT SWING)](#3-kịch-bản-2-săn-cơ-hội-đón-sóng-dẫn-dắt--đột-phá-momentum--breakout-swing)
4. [KỊCH BẢN 3: SĂN CƠ HỘI BẮT ĐÁY KỸ THUẬT / QUÁ BÁN (MEAN REVERSION LONG)](#4-kịch-bản-3-săn-cơ-hội-bắt-đáy-kỹ-thuật--quá-bán-mean-reversion-long)
5. [KỊCH BẢN 4: PHÒNG VỆ DANH MỤC & SĂN CƠ HỘI BÁN KHỐNG (SHORT SWING TRONG DOWNTREND)](#5-kịch-bản-4-phòng-vệ-danh-mục--săn-cơ-hội-bán-khống-short-swing-trong-downtrend)
6. [KỊCH BẢN 5: QUẢN LÝ RỦI RO MÙA BÁO CÁO TÀI CHÍNH (EARNINGS SEASON PLAYBOOK)](#6-kịch-bản-5-quản-lý-rủi-ro-mùa-báo-cáo-tài-chính-earnings-season-playbook)
7. [KỊCH BẢN 6: CHU KỲ CUỐI TUẦN & LẬP KẾ HOẠCH TUẦN MỚI (WEEKEND REVIEW & SECTOR ROTATION)](#7-kịch-bản-6-chu-kỳ-cuối-tuần--lập-kế-hoạch-tuần-mới-weekend-review--sector-rotation)
8. [KỊCH BẢN 7: ĐỊNH KỲ KIỂM TOÁN HIỆU QUẢ TÍN HIỆU & TINH CHỈNH KỶ LUẬT (MONTHLY ALPHA AUDIT)](#8-kịch-bản-7-định-kỳ-kiểm-toán-hiệu-quả-tín-hiệu--tinh-chỉnh-kỷ-luật-monthly-alpha-audit)
9. [KỊCH BẢN 8: QUẢN TRỊ DỮ LIỆU, TỰ ĐỘNG HÓA PIPELINE & XỬ LÝ SỰ CỐ KỸ THUẬT](#9-kịch-bản-8-quản-trị-dữ-liệu-tự-động-hóa-pipeline--xử-lý-sự-cố-kỹ-thuật)

---

## 1. TRIẾT LÝ VẬN HÀNH & NGUYÊN TẮC BẢO VỆ VỐN

Phương pháp phân tích Top-Down của Market Radar tuân thủ nghiêm ngặt 3 nguyên lý sống còn của giao dịch tài chính:

```text
       ┌────────────────────────────────────────────────────────┐
       │ TẦNG 1: THỊ TRƯỜNG CHUNG (MARKET REGIME)               │
       │ "Chỉ bơi xuôi dòng" — Thị trường quyết định 70% kết quả│
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │ TẦNG 2: NGÀNH DẪN DẮT (SECTOR ROTATION)                │
       │ "Dòng tiền lớn đi đâu" — Chọn ngành mạnh nhất chu kỳ   │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │ TẦNG 3: CỔ PHIẾU ĐẦU ĐÀN (STOCK SELECTION)             │
       │ "Cổ phiếu tốt nhất ngành" — Tìm Leader có điểm mua chuẩn│
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │ TẦNG 4: QUẢN TRỊ RỦI RO (EXECUTION & RISK MANAGEMENT)  │
       │ R/R tối thiểu 1:2 — Cắt lỗ dứt khoát tại Invalidation  │
       └────────────────────────────────────────────────────────┘
```

### 3 Nguyên Tắc Cốt Tử:
1. **Không có thiết lập (No Setup) = Không giao dịch:** Khi hệ thống trả về danh sách rỗng (0 ứng viên), đó là lúc thị trường đang phân hóa nguy hiểm hoặc không có lợi thế thống kê. Giữ tiền mặt là một vị thế thông minh.
2. **Kích hoạt trước, Hành động sau:** Chỉ giải ngân khi thị trường chạm mức giá kích hoạt (`Trigger Price`). Tránh mua đón đầu sớm khi cấu trúc giá chưa bứt phá.
3. **Cắt lỗ không thỏa hiệp:** Mức vô hiệu hóa (`Invalidation Price`) là ranh giới kỹ thuật tối hậu. Nếu giá chạm mức này, luận điểm giao dịch bị bác bỏ và vị thế phải được thanh lý ngay lập tức.

---

## 2. KỊCH BẢN 1: QUY TRÌNH CHUẨN BỊ HÀNG NGÀY TRƯỚC PHIÊN MỞ CỬA (PRE-MARKET ROUTINE — 15 PHÚT)

> **Thời điểm thực hiện khuyến nghị:** 
> - Giờ New York: `08:45 – 09:15 ET` (trước giờ mở cửa 15-45 phút).
> - Giờ Việt Nam: `19:45 – 20:15 ICT` (Mùa hè) hoặc `20:45 – 21:15 ICT` (Mùa đông).

```text
[Bước 1: Check Đồng Hồ & Độ Tươi] ──> [Bước 2: Đo Độ Rộng Thị Trường]
                                                    │
[Bước 4: Soi Ứng Viên & Setup]    <── [Bước 3: Rà Soát Trang Hôm Nay]
                 │
                 ▼
[Bước 5: Lên Kế Hoạch Đặt Lệnh Trên TradingView & Broker]
```

### Bước 1: Kiểm tra Đồng Hồ & Trạng Thái Dữ Liệu (1 phút)
1. Mở Market Radar trên trình duyệt.
2. Nhìn thẻ **Đồng Hồ Thị Trường & Trạng Thái NYSE** trên cùng:
   - Xác nhận trạng thái là `Tiền Thị Trường (Pre-market)`.
   - Xem mục tiêu phiên là ngày hôm nay.
3. Nhìn thẻ **Độ Tươi Dữ Liệu**:
   - Nếu thấy huy hiệu màu xanh `Phiên Mới Nhất`: Dữ liệu EOD đã sẵn sàng.
   - Nếu thấy huy hiệu màu vàng/đỏ `Dữ Liệu Lịch Sử (Chậm 1 phiên)`: Bấm ngay nút **"Cập nhật dữ liệu ngay"** ở thanh sidebar bên trái và đợi 1-2 phút để hệ thống cập nhật nến chốt phiên đêm qua.

### Bước 2: Đánh Giá Chế Độ Thị Trường (Market Regime) (3 phút)
1. Chuyển sang Trụ cột **`🌐 Bản Đồ Thị Trường & Ngành`** $\rightarrow$ Chọn **`01 Bức Tranh Thị Trường (Breadth)`**.
2. Quan sát **5 Thanh Bar Đối Chiếu Tỷ Lệ Độ Rộng**:
   - **Kịch bản A — Chế độ Tấn Công (Risk-On / Aggressive Long):**
     - Cả 5 thanh bar đều có phe Xanh $>60\%$.
     - Số mã lập Đỉnh mới (New Highs) áp đảo hoàn toàn Đáy mới (New Lows).
     - SPY và RSP cùng tăng điểm $\rightarrow$ Đà tăng lan tỏa rộng, tự tin giải ngân các vị thế Long Tiếp Diễn.
   - **Kịch bản B — Chế độ Cảnh Giác (Divergence / Selective):**
     - SPY xanh nhưng RSP đỏ; hoặc tỷ lệ trên SMA50 $<50\%$.
     - Đà tăng chỉ tập trung ở vài mã Mega-cap $\rightarrow$ Chỉ giao dịch quy mô nhỏ (1/2 volume chuẩn), ưu tiên chọn các mã `⭐ Leader` cực mạnh hoặc đứng ngoài.
   - **Kịch bản C — Chế độ Phòng Thủ (Risk-Off / Cash is King):**
     - Phe Đỏ chiếm $>60\%$ trên cả 5 thanh bar.
     - Số mã thủng đáy 20 phiên tăng vọt $\rightarrow$ Dừng hoàn toàn việc mua mới; cân nhắc các thiết lập Short Tiếp Diễn hoặc thanh lý vị thế vi phạm.

### Bước 3: Rà Soát Bàn Làm Việc "Hôm Nay" (3 phút)
1. Chuyển sang Trụ cột **`🎯 Hôm Nay & Ứng Viên`** $\rightarrow$ Chọn **`01 Hôm Nay (Sự Kiện)`**.
2. Duyệt qua 4 nhóm tab sự kiện:
   - Tab **`01 Cơ Hội Mới`**: Có cổ phiếu nào mới xuất hiện hôm nay không?
   - Tab **`02 Thay Đổi Setup`**: Có mã nào từ danh mục theo dõi hôm qua nay đã chính thức chuyển sang trạng thái `Triggered` (kích hoạt) không? Có mã nào bị `Invalidated` (hỏng setup) cần xóa bỏ khỏi kế hoạch không?
   - Tab **`03 Sự Kiện Sắp Tới`**: Những mã nào sắp ra BCTC? Đánh dấu để loại bỏ rủi ro.
3. Sau khi đọc xong các sự kiện trọng yếu, bấm **"Đánh dấu tất cả đã đọc ✓"** để dọn sạch bàn làm việc.

### Bước 4: Sàng Lọc & Thẩm Định Ứng Viên Tiềm Năng (5 phút)
1. Chọn tab **`02 Ứng Viên Giao Dịch`**.
2. Chọn nhóm chiến thuật phù hợp với chế độ thị trường đã xác định ở Bước 2 (thường là `Long Tiếp Diễn`).
3. Bật hộp kiểm **`Chỉ xem Leader ⭐`** để lọc ra các cổ phiếu đầu đàn thuộc Top 20% ngành mạnh.
4. Chọn ra 1 đến 3 cổ phiếu có điểm `Score` cao nhất:
   - Bấm nút **`Chi tiết {Ticker} 🔍`** để mở modal phân tích.
   - **Tab Kỹ thuật:** Xem mức `Trigger Price` (giá kích hoạt) và `Invalidation Price` (giá cắt lỗ). Kiểm tra xem khoảng cách cắt lỗ (`Risk %`) có nằm trong mức chấp nhận của tài khoản không (khuyến nghị $\le 5\% - 8\%$).
   - **Tab Nến Nhật & FA:** Đọc 3 dòng thông dịch nến gần nhất (đảm bảo không bị cảnh báo mua đuổi quá xa MA20); kiểm tra hồ sơ áp lực mua bán 1/3/5 phiên (đảm bảo bên mua đang áp đảo).

### Bước 5: Lập Kế Hoạch & Đặt Lệnh Chờ (3 phút)
1. Bấm nút **`Mở biểu đồ TradingView ↗`** trên thẻ ứng viên để mở đồ thị nến ngày của cổ phiếu.
2. Kiểm tra lại hành vi giá trực quan: Xu hướng nến, các ngưỡng cản trên đầu.
3. Đăng nhập ứng dụng Broker (Interactive Brokers, Charles Schwab, TCBS/VPS đối với trader theo dõi US,...):
   - Không đặt lệnh mua theo thị trường (Market Order) lúc mở cửa.
   - **Đặt lệnh dừng mua (Buy Stop Order):** Đặt tại mức `Trigger Price` của Market Radar. Nếu giá vượt qua mức này kèm volume trong phiên thì lệnh tự khớp; nếu giá quay đầu giảm thì lệnh không khớp, bảo vệ tuyệt đối vốn.
   - Đặt sẵn lệnh cắt lỗ tự động (Stop Loss) tại mức `Invalidation Price`.

---

## 3. KỊCH BẢN 2: SĂN CƠ HỘI ĐÓN SÓNG DẪN DẮT / ĐỘT PHÁ (MOMENTUM & BREAKOUT SWING)

> **Mục tiêu:** Mua các cổ phiếu mạnh nhất thị trường khi chúng vừa hoàn tất mẫu hình tích lũy và bứt phá vượt đỉnh 20 phiên, nhằm đón nhịp tăng mạnh nhất (sóng 3 hoặc sóng đẩy).

```text
[RRG Sector: Dẫn Dắt (Leading)] ──> [O'Neil Heatmap: Sub-Industry COMP ≥ 80]
                                                  │
[Checklist: Vol ≥ 1.5x, Áp Lực Mua] <── [Lọc Ứng Viên: Long Tiếp Diễn ⭐ Leader]
                 │
                 ▼
[Vào lệnh: Buy Stop tại Trigger, Stop Loss tại Invalidation]
```

### Bước 1: Xác định Nhóm Ngành Dẫn Dắt
1. Vào **`🌐 Bản Đồ Thị Trường & Ngành`** $\rightarrow$ **`02 11 Ngành GICS`**.
2. Nhìn vào biểu đồ luân chuyển 4 góc phần tư RRG:
   - Tìm các bong bóng ngành nằm trong góc phần tư **`DẪN DẮT (LEADING - Màu Xanh Lá)`** hoặc đang từ góc **`CẢI THIỆN (IMPROVING - Màu Xanh Dương)`** đâm chéo lên góc Dẫn dắt.
   - Kiểm tra vệt lịch sử 10 phiên: Vệt mũi tên phải hướng lên trên về bên phải (động lượng và sức mạnh tương đối đều tăng).
   - *Ví dụ: Ngành Công nghệ (XLK) hoặc Công nghiệp (XLI) đang ở góc Leading.*
3. Vào **`03 Ma Trận 127 Nhóm Ngành O'Neil`**:
   - Tìm các phân ngành nhỏ (Sub-Industry) có điểm **`COMP $\ge 80$`** (nằm trong Top 20% ngành mạnh nhất thị trường).

### Bước 2: Lọc Ứng Viên Đầu Đàn (Leaders)
1. Vào **`🎯 Hôm Nay & Ứng Viên`** $\rightarrow$ **`02 Ứng Viên Giao Dịch`**.
2. Chọn tab **`Long Tiếp Diễn (Trend Continuation)`**.
3. Bật hộp kiểm **`Chỉ xem Leader ⭐`**.
4. Tìm các mã có subtype là:
   - `breakout`: Vừa vượt đỉnh 20 phiên trước kèm khối lượng lớn.
   - `near_breakout`: Đang tích lũy sát đỉnh 20 phiên (trong biên độ $1.5\%$), sẵn sàng bứt phá.
   - `pullback_ma20`: Cổ phiếu dẫn dắt vừa có nhịp điều chỉnh lành mạnh về chạm đường trung bình MA20 và bật tăng trở lại.

### Bước 3: Thẩm Định Bằng Chứng Kỹ Thuật & Cấu Trúc Áp Lực
1. Bấm mở **`Chi tiết setup 🔍`**:
   - **Kiểm tra Thanh khoản & Khối lượng:** Tỷ lệ Relative Volume (`RVOL`) phải $\ge 1.5$ (khối lượng cao hơn ít nhất $50\%$ so với bình quân 20 phiên). Giá trị giao dịch khớp lệnh (`Dollar Volume`) phải đạt tối thiểu 10 triệu USD/phiên để đảm bảo thanh khoản ra vào dễ dàng.
   - **Kiểm tra Mẫu Nến:** Nến phiên gần nhất phải là nến tăng thân dài (`Marubozu`), nến bứt phá hoặc nến rút chân (`Hammer`); mức giá đóng cửa nằm ở nửa trên biên độ phiên (`close_position_pct` $\ge 65\%$).
   - **Kiểm tra Hồ sơ Áp Lực Đa Phiên:** Khối `🟢 BẰNG CHỨNG HỖ TRỢ` có ghi nhận: *Tích lũy volume mua lớn*, *Không xuất hiện râu nến trên dài*.
   - **Kiểm tra Điểm cách MA20:** Khoảng cách tới đường MA20 không vượt quá $1.5$ ATR (tránh mua khi giá đã quá rướn).

### Bước 4: Lập Kế Hoạch Quản Trị Lệnh (Trade Management)
- **Điểm Vào (Entry):** 
  - Với setup `breakout`: Đặt mua quanh giá đóng cửa hoặc canh nhịp test nhẹ đầu phiên.
  - Với setup `near_breakout`: Đặt lệnh chờ mua `Buy Stop` tại mức `Trigger Price` (ngay trên đỉnh 20 phiên $+0.05\$$).
- **Điểm Cắt Lỗ (Stop Loss):** Đặt tại mức `Invalidation Price` (thường là dưới đáy nến bứt phá hoặc dưới MA20).
- **Mục Tiêu Lợi Nhuận (Take Profit):** Tối thiểu bằng $2 \times$ mức rủi ro cắt lỗ ($R/R \ge 1:2$). Khi giá đạt lợi nhuận $+1.5$ ATR, chủ động dời Stop Loss lên điểm hòa vốn (Breakeven).

---

## 4. KỊCH BẢN 3: SĂN CƠ HỘI BẮT ĐÁY KỸ THUẬT / QUÁ BÁN (MEAN REVERSION LONG)

> **Mục tiêu:** Mua cổ phiếu có nền tảng cơ bản tốt sau một nhịp giảm sâu đột ngột (sell-off), khi giá chạm hỗ trợ cứng và xuất hiện dòng tiền bắt đáy quay trở lại.

```text
[Thị trường Quá Bán: Tỷ lệ trên MA20 < 20%] ──> [Lọc Ứng Viên: Long Đảo Chiều]
                                                               │
[Kiểm tra Mẫu Nến: Hammer / Bullish Engulfing] <───────────────┘
                 │
                 ▼
[Vào lệnh: Mua sau khi nến đảo chiều đóng cửa, Stop Loss dưới Đáy nến]
```

### Bước 1: Nhận Diện Vùng Thị Trường Quá Bán Cực Đoan
1. Vào **`🌐 Bản Đồ Thị Trường & Ngành`** $\rightarrow$ **`01 Bức Tranh Thị Trường (Breadth)`**.
2. Quan sát đồ thị chuỗi thời gian:
   - Đường **`% Cổ phiếu trên MA20`** giảm xuống dưới vùng **$20\%$** (vùng kiệt quệ phe bán).
   - Đường **`Net Breadth`** âm sâu liên tục 3-5 phiên.
   - Thanh bar **`Đáy 20 Phiên (New Lows)`** tăng vọt lên mức cực đại $\rightarrow$ Báo hiệu đà bán tháo hoảng loạn (Capitulation), nhịp hồi phục kỹ thuật sắp diễn ra.

### Bước 2: Sàng Lọc Mã "Long Đảo Chiều"
1. Vào **`🎯 Hôm Nay & Ứng Viên`** $\rightarrow$ **`02 Ứng Viên Giao Dịch`**.
2. Chọn tab **`Long Đảo Chiều (Reversal / Mean Reversion)`**.
3. Ưu tiên các mã có subtype:
   - `reversal_reclaim`: Cổ phiếu sau khi gãy MA20 đã có phiên bứt phá lấy lại đường MA20 kèm khối lượng lớn.
   - `reversal_rebound`: Bật tăng mạnh $>+2\%$ từ vùng hỗ trợ đáy 20 phiên.

### Bước 3: Thẩm Định Điều Kiện Bắt Đáy An Toàn
1. Mở **`Chi tiết setup 🔍`**:
   - **Kiểm tra Nến Nhật:** Phiên chốt đáy bắt buộc phải xuất hiện mẫu nến đảo chiều tin cậy:
     - Nến **Hammer (Pinbar)** có râu dưới dài $\ge 55\%$ tổng biên độ phiên, thể hiện phe bán bị đẩy lùi hoàn toàn vào cuối phiên.
     - Hoặc nến **Bullish Engulfing** (Nhấn chìm tăng) bao trọn toàn bộ thân nến giảm trước đó.
   - **Kiểm tra Bối cảnh FA:** Cổ phiếu phải có Doanh thu và EPS tăng trưởng dương, biên lợi nhuận lành mạnh. *Tuyệt đối không bắt đáy các cổ phiếu có cảnh báo đòn bẩy tài chính nguy hiểm hoặc biên lợi nhuận âm nặng.*
   - **Kiểm tra Kháng cự trên đầu:** Kiểm tra mức `Resistance Level` (thường là đường MA50 đang dốc xuống). Đảm bảo khoảng cách từ giá hiện tại đến kháng cự đủ rộng (tối thiểu $+6\% - 8\%$) để có biên độ lợi nhuận.

### Bước 4: Chiến Lược Thoát Lệnh Nhanh (In-and-Out Swing)
- **Bản chất lệnh đảo chiều là đánh ngược xu hướng chính:** Phải chốt lời nhanh, không kỳ vọng ôm dài hạn.
- **Điểm Dừng Lỗ:** Đặt ngay dưới đáy thấp nhất của cây nến đảo chiều (`Invalidation Price`). Nếu giá xuyên thủng đáy này $\rightarrow$ Cắt lỗ ngay lập tức, không gồng lệnh.
- **Chốt Lời:** Đặt lệnh bán chốt lời từng phần (Scale out) khi giá chạm đường trung bình MA50 hoặc khi đạt tỷ lệ $R/R = 1:1.5$ đến $1:2$.

---

## 5. KỊCH BẢN 4: PHÒNG VỆ DANH MỤC & SĂN CƠ HỘI BÁN KHỐNG (SHORT SWING TRONG DOWNTREND)

> **Mục tiêu:** Tìm kiếm lợi nhuận từ đà giảm giá hoặc bảo vệ tài khoản khi thị trường chung bước vào giai đoạn Downtrend xác nhận.

```text
[Thị Trường Suy Thoái: Phe Đỏ > 65%] ──> [Lọc Ngành: Tụt Hậu (Lagging)]
                                                      │
[Kiểm tra Broker: Khả Năng Vay Short] <── [Lọc Ứng Viên: Short Tiếp Diễn]
                 │
                 ▼
[Vào lệnh: Sell Stop tại Trigger, Dừng Lỗ chặt chẽ tại Invalidation]
```

### Bước 1: Xác Định Môi Trường Thuận Lợi Cho Chiều Short
1. Vào **`01 Bức Tranh Thị Trường (Breadth)`**:
   - Thanh bar **`SMA50`** có số mã dưới đường trung hạn chiếm $>60\%$.
   - SPY và RSP liên tục tạo các đỉnh và đáy thấp dần.
   - Xuất hiện hiện tượng **Mega-Cap Masking**: Nhóm công nghệ lớn bị bán tháo, kéo chỉ số lao dốc.
2. Vào **`02 11 Ngành GICS`**:
   - Xác định các ngành nằm trong góc phần tư **`TỤT HẬU (LAGGING - Màu Đỏ)`** trên biểu đồ RRG (ví dụ: Bất động sản XLRE, Năng lượng XLE, Vật liệu XLB).

### Bước 2: Sàng Lọc Ứng Viên Short
1. Vào **`02 Ứng Viên Giao Dịch`** $\rightarrow$ Chọn tab **`Short Tiếp Diễn (Downtrend Continuation)`**.
2. Tìm các mã có cấu trúc:
   - `breakdown`: Thủng vùng hỗ trợ đáy 20 phiên kèm áp lực bán gia tăng.
   - `pullback_ma20_res`: Cổ phiếu nằm trong xu hướng giảm dài hạn, vừa có nhịp hồi phục yếu ớt chạm cản MA20 rồi quay đầu giảm tiếp.

### Bước 3: Kiểm Tra Tính Khả Thi Tại Sàn Giao Dịch (BẮT BUỘC)
1. Đọc kỹ dòng cảnh báo của Market Radar: `⚠️ Lưu ý Short: Chưa xác minh khả năng short / phí vay thực tế tại broker`.
2. Đăng nhập vào nền tảng giao dịch của Broker cá nhân (Interactive Brokers, Thinkorswim,...):
   - Kiểm tra xem mã cổ phiếu có trạng thái **ETB (Easy to Borrow)** hay không.
   - Nếu mã bị gắn nhãn **HTB (Hard to Borrow)**: Kiểm tra mức phí vay qua đêm (Borrow Fee Rate). Nếu phí vay quá cao ($>10\% - 20\%$/năm), hãy bỏ qua mã này để tránh chi phí ngầm ăn mòn lợi nhuận.

### Bước 4: Thực Thi Lệnh Short & Quản Trị Rủi Ro Cắt Lỗ
- **Điểm Vào Lệnh (Short Entry):** Đặt lệnh `Sell Stop` ngay dưới đáy phiên phá vỡ (`Trigger Price`).
- **Điểm Dừng Lỗ (Stop Loss):** Đặt tại mức `Invalidation Price` (ngay trên đỉnh nến hồi phục gần nhất hoặc trên đường MA20).
- **Quy Tắc Quản Trị Rủi Ro Vô Hạn:** Bán khống có rủi ro lỗ không giới hạn nếu cổ phiếu bị hiện tượng bẫy ép mua (Short Squeeze). **Tuyệt đối không giao dịch short mà không cài sẵn lệnh Stop Loss tự động.**

---

## 6. KỊCH BẢN 5: QUẢN LÝ RỦI RO MÙA BÁO CÁO TÀI CHÍNH (EARNINGS SEASON PLAYBOOK)

> **Mục tiêu:** Loại bỏ rủi ro "tai nạn tài khoản" do những cú nhảy gap giá $-15\%$ đến $-30\%$ khi doanh nghiệp công bố báo cáo tài chính bất ngờ.

```text
[Tab 03: Lịch Báo Cáo Tài Chính] ──> [Lọc: Chỉ Ứng Viên Radar]
                                                  │
[Tra cứu SEC EDGAR: Check 10-Q]  <── [Xác định Thời điểm BMO / AMC]
                 │
                 ▼
[Nguyên tắc: KHÔNG MỞ MỚI nếu BCTC trong 1-5 phiên; Hạ tỷ trọng nếu đang giữ]
```

### Bước 1: Rà Soát Lịch Báo Cáo Tài Chính của Danh Mục Ứng Viên
1. Vào **`🎯 Hôm Nay & Ứng Viên`** $\rightarrow$ Chọn **`03 Lịch Báo Cáo Tài Chính (Earnings)`**.
2. Thiết lập thanh bộ lọc:
   - Khung thời gian: Chọn **`Tuần Này`** hoặc **`14 Ngày Tới`**.
   - Bộ lọc phạm vi: Chọn **`Chỉ Ứng Viên Radar`**.
3. Xem trên giao diện **`Lịch Tuần (Weekly Grid)`**:
   - Hệ thống sẽ hiển thị những cổ phiếu nào trong danh sách ứng viên swing có lịch ra tin trong tuần.

### Bước 2: Phân Tích Thời Điểm Ra Tin (Timing Analysis)
- **`☀️ TRƯỚC GIỜ MỞ CỬA (BMO - Before Market Open)`:**
  - Báo cáo công bố khoảng 06:30 – 08:00 ET.
  - **Hành vi giá:** Cổ phiếu sẽ nhảy gap ngay khi thị trường mở cửa phiên hôm đó (09:30 ET).
- **`🌙 SAU GIỜ ĐÓNG CỬA (AMC - After Market Close)`:**
  - Báo cáo công bố khoảng 16:05 – 17:00 ET.
  - **Hành vi giá:** Cổ phiếu sẽ biến động dữ dội trong phiên ngoài giờ (After-hours) và nhảy gap vào phiên sáng ngày hôm sau.

### Bước 3: Quy Tắc Hành Động Chuẩn Mực (Standard Action Rules)
1. **Đối với vị thế dự định mở mới:**
   - **Quy tắc Vàng:** **KHÔNG BAO GIỜ** mở mới vị thế swing đối với cổ phiếu dự kiến ra BCTC trong vòng **1 đến 5 phiên giao dịch tới**. 
   - Đưa cổ phiếu vào danh sách theo dõi, đợi sau khi BCTC ra tin và thị trường hấp thụ xong phản ứng giá mới xem xét vào lệnh (chiến lược Post-Earnings Announcement Drift - PEAD).
2. **Đối với vị thế đang nắm giữ và có lãi:**
   - Nếu cổ phiếu sắp ra BCTC sau giờ đóng cửa (AMC): Chủ động bán chốt lời tối thiểu **$50\% - 70\%$** lượng cổ phiếu đang giữ trước 16:00 ET để khóa lợi nhuận.
   - Dời Stop Loss của phần còn lại lên mức giá vốn (Breakeven).
3. **Đối với vị thế đang hòa vốn hoặc lỗ nhẹ:**
   - Đóng toàn bộ vị thế trước giờ ra tin để tránh rủi ro mở rộng khoản lỗ ngoài tầm kiểm soát do trượt giá gap.

---

## 7. KỊCH BẢN 6: CHU KỲ CUỐI TUẦN & LẬP KẾ HOẠCH TUẦN MỚI (WEEKEND REVIEW & SECTOR ROTATION)

> **Thời điểm thực hiện khuyến nghị:** Thứ Bảy hoặc Chủ Nhật hàng tuần.  
> **Mục tiêu:** Nhìn lại bức tranh toàn cảnh của tuần giao dịch vừa kết thúc, phát hiện dòng tiền tổ chức đang âm thầm dịch chuyển vào đâu, và lập danh sách theo dõi (Watchlist) sẵn sàng cho tuần mới.

```text
[Tab 02 So Sánh Snapshot Delta] ──> [Đánh giá Ma trận 127 Ngành O'Neil]
                                                  │
[Lập Watchlist Tuần Mới]        <── [Lọc Ứng Viên Top Score & Leader]
                 │
                 ▼
[Xuất CSV sang Excel & Đồng bộ biểu đồ trên TradingView]
```

### Bước 1: Đánh Giá Biến Động Qua Công Cụ So Sánh Snapshot (Delta)
1. Chuyển sang Trụ cột **`📊 Đo Lường & Kiểm Toán`** $\rightarrow$ Chọn **`02 So Sánh Snapshot (Delta)`**.
2. Chọn đối chiếu giữa snapshot phiên Thứ Sáu và snapshot Thứ Sáu tuần trước:
   - Xem số lượng **Mã mới lọt danh sách (`Added`)**: Đa số các mã mới thuộc ngành nào?
   - Xem số lượng **Mã rời danh sách (`Removed`)**: Các mã bị loại có tập trung ở ngành nào không? (Dấu hiệu dòng tiền tháo chạy khỏi ngành đó).
   - Xem bảng **Biến động thứ hạng ngành**: Ngành nào thăng hạng mạnh nhất trong tuần qua?

### Bước 2: Soi Dòng Tiền Ngầm Với Ma Trận 127 Nhóm Ngành O'Neil
1. Chuyển sang Trụ cột **`🌐 Bản Đồ Thị Trường & Ngành`** $\rightarrow$ Chọn **`03 Ma Trận 127 Nhóm Ngành O'Neil`**.
2. Chọn chế độ xem **`COMP / BLEND`**:
   - Tìm các ô màu xanh lá đậm (Điểm COMP $\ge 85$).
   - Click vào các **Stock Pills** (viên thuốc mã cổ phiếu đầu đàn) bên trong ô để mở đồ thị nến tuần (W1) trên TradingView.
   - Nhận diện các nhóm ngành con đang tích lũy mẫu hình kiến tạo (ví dụ: Nền giá phẳng, Cốc tay cầm, Thu hẹp độ biến động VCP).

### Bước 3: Lập Danh Sách Ưu Tiên Cho Tuần Mới (Priority Watchlist)
1. Vào **`🎯 Hôm Nay & Ứng Viên`** $\rightarrow$ **`02 Ứng Viên Giao Dịch`**.
2. Lọc danh sách `Long Tiếp Diễn`, bật `Chỉ xem Leader ⭐`.
3. Bấm nút **`Xuất CSV 📥`** để tải toàn bộ bảng dữ liệu.
4. Mở file CSV bằng Excel:
   - Sắp xếp theo cột `Score` từ cao xuống thấp.
   - Chọn ra 5 đến 7 mã cổ phiếu có cấu trúc đẹp nhất.
   - Ghi chú lại mức `Trigger` và `Invalidation` cho từng mã.
5. Tạo một danh sách theo dõi riêng trên TradingView (ví dụ: `Radar_Watchlist_W38`) và add các mã này vào để tiện theo dõi cảnh báo giá (Alerts) trong suốt tuần.

---

## 8. KỊCH BẢN 7: ĐỊNH KỲ KIỂM TOÁN HIỆU QUẢ TÍN HIỆU & TINH CHỈNH KỶ LUẬT (MONTHLY ALPHA AUDIT)

> **Thời điểm thực hiện khuyến nghị:** Định kỳ cuối mỗi tháng hoặc cuối quý.  
> **Mục tiêu:** Đo lường khách quan hiệu quả thực tế của bộ lọc, xác định "lợi thế thống kê" (Edge) của hệ thống và loại bỏ những hành vi giao dịch không mang lại lợi nhuận.

```text
[Tab 01 Hiệu Quả Tín Hiệu (Alpha Audit)] ──> [So sánh Forward Return 5D, 10D, 20D]
                                                              │
[Khảo sát Lợi thế Nến Nhật (Candlestick Edge)] <──────────────┘
                               │
                               ▼
[Kiểm định Tính Đơn Điệu của Score: Top Q1 vs Bottom Q4]
```

### Bước 1: Đo Lường Alpha So Với Thị Trường Chung
1. Vào **`📊 Đo Lường & Kiểm Toán`** $\rightarrow$ Chọn **`01 Hiệu Quả Tín Hiệu (Alpha Audit)`**.
2. Quan sát bảng tổng hợp hiệu suất đa kỳ hạn:
   - So sánh lợi nhuận của bộ lọc ở các mốc: **5 phiên (5D), 10 phiên (10D), và 20 phiên (20D)**.
   - Xem chỉ số **Alpha so với SPY**:
     - Nếu Alpha $>0$ (ví dụ: $+2.5\%$): Bộ lọc đang đánh bại thị trường, tiếp tục duy trì phương pháp.
     - Nếu Alpha $\le 0$: Thị trường đang ở pha đi ngang khó chịu (Choppy/Sideway), cần thu hẹp quy mô giao dịch và rút ngắn thời gian giữ lệnh.
3. Xem bảng **Chu kỳ Swing Trong Tuần (In-Week Swing)**:
   - So sánh tỷ lệ thắng khi giữ lệnh 1D, 2D, 3D, 4D và Chốt cuối tuần (`Week-Close 99`).
   - Nhìn bảng phân rã theo Thứ: Nhận diện xem mở vị thế vào Thứ Hai, Thứ Ba hay Thứ Tư đem lại xác suất thắng cao nhất.

### Bước 2: Tối Ưu Hóa Tỷ Lệ Cắt Lỗ Qua MFE / MAE
1. Quan sát 2 chỉ số dao động cực đại:
   - **MFE (Lãi tiềm năng tối đa):** Trung bình các setup chạy được bao nhiêu ATR trước khi thoái lui? Nếu MFE trung bình là $2.2$ ATR $\rightarrow$ Mức chốt lời hợp lý nên đặt quanh $1.8 - 2.0$ ATR.
   - **MAE (Lỗ chịu đựng tối đa):** Trung bình vị thế bị nhúng âm bao nhiêu ATR trước khi bật tăng? Nếu MAE trung bình chỉ là $-0.8$ ATR $\rightarrow$ Mức dừng lỗ $1.2 - 1.5$ ATR là hoàn toàn an toàn, không sợ bị quét oan.

### Bước 3: Khảo Sát Lợi Thế Nến Nhật (Candlestick Edge Audit)
1. Kéo xuống bảng **Khảo Sát Lợi Thế Mẫu Nến Nhật**:
   - Đối chiếu tỷ lệ thắng và Alpha của các mẫu nến: *Hammer, Bullish Engulfing, Marubozu, Doji, Inside Bar*.
   - **Hành động tinh chỉnh:** Nếu số liệu thống kê cho thấy mẫu nến *Hammer* có tỷ lệ thắng $68\%$ và Alpha $+3.2\%$, trong khi *Inside Bar* chỉ có tỷ lệ thắng $42\%$ $\rightarrow$ Trong tháng tiếp theo, ưu tiên chọn các setup có nến Hammer xác nhận, hạn chế giao dịch các setup Inside Bar.

### Bước 4: Kiểm Tra Giá Trị Của Điểm Số (Score Validation)
1. Xem biểu đồ kiểm định tính đơn điệu (Monotonicity Test):
   - So sánh nhóm **Top 25% Điểm Cao Nhất (Quartile 1)** với nhóm **Bottom 25% Điểm Thấp Nhất (Quartile 4)**.
   - Khẳng định tính kỷ luật: Chỉ chọn giao dịch các mã nằm trong Top điểm số cao, tuyệt đối không "vớt vát" các mã ở nhóm điểm thấp.

---

## 9. KỊCH BẢN 8: QUẢN TRỊ DỮ LIỆU, TỰ ĐỘNG HÓA PIPELINE & XỬ LÝ SỰ CỐ KỸ THUẬT

> **Mục tiêu:** Đảm bảo hệ thống vận hành ổn định, tự động cập nhật dữ liệu EOD hàng ngày và biết cách xử lý khi gặp sự cố kết nối hoặc lỗi dữ liệu.

```text
[Sau 16:30 ET: Nạp Dữ Liệu EOD] ──> [Kiểm tra Huy Hiệu Hoàn Chỉnh (Complete)]
                                                 │
[Xử lý Ngoại lệ / Backup DB]    <── [Phát hiện Cảnh báo Degraded / Missing]
```

### Bước 1: Quy Trình Cập Nhật Dữ Liệu Hàng Ngày
Dữ liệu nến ngày chốt phiên Mỹ (EOD) thường được Yahoo Finance hoàn tất xử lý sau **16:30 ET** (tức khoảng **03:30 - 04:30 sáng giờ Việt Nam**). Có 3 cách cập nhật:

- **Cách 1 — Cập nhật thủ công trên giao diện Web (Khuyến nghị):**
  - Mở dashboard Market Radar.
  - Bấm nút **"Cập nhật dữ liệu ngay"** ở đầu thanh sidebar.
  - Chờ pipeline chạy xong và trang web tự động tải lại với snapshot mới.
- **Cách 2 — Chạy qua dòng lệnh Terminal:**
  ```powershell
  python -m jobs.update_pipeline
  ```
- **Cách 3 — Chạy tự động định kỳ ngầm (Tự động hóa hoàn toàn):**
  - Khởi động file `run_scheduler.bat` hoặc chạy scheduler Python:
    ```powershell
    python -m jobs.scheduler --interval 6
    ```
  - Hoặc thiết lập **Windows Task Scheduler** gọi file `jobs/run_update.bat` tự động vào lúc 05:00 sáng mỗi ngày từ Thứ Ba đến Thứ Bảy.

### Bước 2: Kiểm Tra & Đọc Hiểu Huy Hiệu Chất Lượng Dữ Liệu
Sau mỗi lần cập nhật, hãy kiểm tra mục **Trạng thái Dữ liệu** tại sidebar:
- **`Complete (Đồng phiên)` (Xanh lá):** Hệ thống đạt trạng thái hoàn hảo. Đủ 503 mã, tỷ lệ bao phủ $>95\%$, đầy đủ lịch sử 253 phiên.
- **`Degraded` (Đỏ nhạt):** Tỷ lệ bao phủ bị tụt xuống dưới $95\%$ (do Yahoo Finance bị gián đoạn mạng hoặc phản hồi chậm).
  - *Xử lý:* Đợi 5-10 phút rồi bấm lại nút "Cập nhật dữ liệu ngay" để tải bù các mã bị thiếu.
- **`Cũ (X phiên)` (Vàng):** Thị trường đã đóng cửa phiên mới nhưng bạn chưa chạy cập nhật. Bấm nút cập nhật để nạp phiên mới nhất.
- **`Lỗi Bất Biến (Legacy)`:** Snapshot cũ bị lệch cấu trúc. Chạy pipeline mới sẽ tự động khắc phục.

### Bước 3: Sao Lưu & Bảo Vệ Cơ Sở Dữ Liệu SQLite
- Toàn bộ cơ sở dữ liệu lịch sử của bạn được lưu tại file: `data/market_radar.db`.
- **Cơ chế Khóa An Toàn (`ProcessLock`):** Hệ thống tự động tạo file khóa `data/pipeline.lock` khi đang cập nhật để ngăn hai tiến trình chạy đè lên nhau. Nếu tiến trình bị tắt đột ngột và file lock còn sót lại, hệ thống sẽ tự động giải phóng sau thời gian timeout an toàn.
- **Quy trình Sao lưu Khuyến nghị (Hàng tuần):**
  1. Đóng ứng dụng Streamlit.
  2. Copy file `data/market_radar.db` sang một bản lưu trữ dự phòng (ví dụ: `data/market_radar_backup_YYYYMMDD.db`).
  3. Nếu gặp sự cố hỏng database, chỉ cần copy đè bản backup trở lại là toàn bộ lịch sử snapshot và nhật ký tín hiệu sẽ được khôi phục nguyên vẹn.
