# Hướng Dẫn Triển Khai Market Radar Lên Render + GitHub Actions (100% Free)

Tài liệu này hướng dẫn chi tiết từng bước đưa hệ thống **Market Radar** từ VPS sang chạy hoàn toàn trên đám mây với:
* **Tầng hiển thị:** Web UI Streamlit chạy trên **Render Web Service** (Miễn phí).
* **Tầng tự động hóa:** Chạy cào dữ liệu và phân tích tự động theo 4 khung giờ chuẩn (`05:00`, `11:00`, `17:00`, `23:00` VN) bằng **GitHub Actions** (Miễn phí).
* **Tầng lưu trữ dữ liệu:** Lưu trữ bản nén SQLite database tự động qua **GitHub Releases** (Miễn phí, không lo giới hạn ephemeral disk của Render và không làm phình git repository).

---

## Bước 1: Tạo bản Snapshot Database ban đầu trên GitHub Releases

Để Render có thể tải và hiển thị dữ liệu ngay trong lần khởi động đầu tiên, bạn cần upload file database hiện tại lên GitHub Release.

### Cách 1: Dùng lệnh GitHub CLI (Nếu máy bạn đã cài `gh`)
Mở terminal tại thư mục dự án và chạy:
```bash
# Nén file database hiện tại (file kết quả lưu tại data/market_radar.db.gz ~11MB)
python scripts/sync_release_db.py --compress

# Tạo release tag 'data-latest' và upload file lên
gh release create data-latest data/market_radar.db.gz --title "Market Radar Database Snapshot (Latest)" --notes "Bản dữ liệu khởi tạo ban đầu."
```

### Cách 2: Upload trực tiếp qua giao diện web GitHub (Rất đơn giản)
1. Chạy lệnh nén database trong terminal máy bạn:
   ```bash
   python scripts/sync_release_db.py --compress
   ```
   *(File nén `market_radar.db.gz` sẽ xuất hiện trong thư mục `data/`)*
2. Truy cập vào GitHub repo của bạn: `https://github.com/tthanhvu002sgu/market-radar/releases`.
3. Nhấn **Draft a new release** (hoặc *Create a new release*):
   * **Choose a tag**: gõ `data-latest` rồi nhấn **Create new tag: data-latest on publish**.
   * **Release title**: gõ `Market Radar Database Snapshot (Latest)`.
   * Ở mục **Attach binaries by dropping them here or selecting them**: Kéo thả file `data/market_radar.db.gz` vào.
4. Nhấn **Publish release**.

---

## Bước 2: Đẩy các file cấu hình mới lên GitHub

Chạy các lệnh sau để commit toàn bộ file thiết lập lên repo:

```bash
git add .streamlit/config.toml .github/workflows/market_radar_cron.yml render.yaml start.sh scripts/sync_release_db.py docs/RENDER_DEPLOY_GUIDE.md .gitignore
git commit -m "feat: setup Render web service & GitHub Actions cron automation"
git push origin main
```

---

## Bước 3: Triển khai Web Service trên Render

1. Đăng nhập vào [Render.com](https://render.com/) (đăng nhập bằng tài khoản GitHub).
2. Tại màn hình Dashboard, nhấn **New +** -> Chọn **Web Service**.
3. Chọn kho mã nguồn **`market-radar`** (nhấn *Connect*).
4. Điền các thông tin cấu hình như sau:
   * **Name:** `market-radar` (hoặc tên tùy thích).
   * **Region:** `Singapore` (để tốc độ tải từ VN nhanh nhất).
   * **Branch:** `main`.
   * **Runtime:** `Python 3`.
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `bash start.sh`
   * **Instance Type:** Chọn **Free** ($0/month).
5. Cuộn xuống phần **Environment Variables** (Biến môi trường), thêm các biến:
   * `PYTHON_VERSION`: `3.11.9`
   * `GITHUB_REPO`: `tthanhvu002sgu/market-radar`
   * `RELEASE_TAG`: `data-latest`
   * *(Chỉ cần nếu Repo của bạn là **Private**)*: Thêm `GITHUB_TOKEN` với giá trị là Personal Access Token có quyền đọc contents của repo. Nếu repo là **Public**, bạn **không cần** thêm token này.
6. Nhấn nút **Create Web Service**.
7. Render sẽ tiến hành build và khởi chạy. Khi thấy log hiện:
   ```text
   === [1/2] Đồng bộ dữ liệu Market Radar từ GitHub Releases ===
   ... Đã cập nhật database thành công vào: .../data/market_radar.db
   === [2/2] Khởi động Streamlit Server trên Render ===
   ```
   Bạn có thể nhấn vào link `https://market-radar-xxxx.onrender.com` để trải nghiệm web.

---

## Bước 4: Liên kết Tự Động Cập Nhật (Render Deploy Hook)

Để mỗi khi GitHub Actions hoàn thành tính toán dữ liệu mới, website trên Render tự động khởi động lại và nạp dữ liệu mới nhất:

1. **Lấy Deploy Hook URL từ Render:**
   * Trong trang quản lý Web Service trên Render, vào mục **Settings**.
   * Cuộn xuống phần **Deploy Hook**.
   * Nhấn **Create Deploy Hook** (hoặc copy URL sẵn có), định dạng URL dạng: `https://api.render.com/deploy/srv-xxxxxxx?key=yyyyyyy`.
2. **Lưu vào GitHub Secrets:**
   * Mở repository của bạn trên GitHub.
   * Vào **Settings** (của repo) -> **Secrets and variables** -> **Actions**.
   * Nhấn **New repository secret**.
   * **Name:** `RENDER_DEPLOY_HOOK`
   * **Secret:** Dán đường link URL vừa copy từ Render vào.
   * Nhấn **Add secret**.

> Xong! Kể từ lúc này, mỗi khi GitHub Actions chạy xong 4 cữ trong ngày, nó sẽ tự động kích hoạt Render kéo database mới nhất về hiển thị cho bạn.

---

## Bước 5: Mẹo giữ Web luôn mở, không bị Sleep (Tùy chọn)

Trên gói Render Free, nếu không có ai truy cập trong 15 phút, container sẽ tạm thời rơi vào trạng thái ngủ để tiết kiệm tài nguyên (lần truy cập sau đó sẽ mất khoảng 30-50s để khởi động lại).

Để app luôn luôn thức và phản hồi tức thì bất cứ lúc nào bạn mở điện thoại/máy tính:
1. Đăng ký tài khoản miễn phí tại [UptimeRobot.com](https://uptimerobot.com/) hoặc [cron-job.org](https://cron-job.org/).
2. Tạo một **HTTP Monitor** trỏ vào đường link trang web Render của bạn (ví dụ: `https://market-radar.onrender.com`).
3. Chọn tần suất ping: Mỗi **10 phút** hoặc **14 phút** / 1 lần.
4. Render sẽ luôn nhận được tín hiệu truy cập và duy trì trạng thái thức 24/7.

---

## Kiểm thử hệ thống hoạt động ngay (Test Run)

Bạn không cần chờ đến đúng khung giờ cron để kiểm tra:
1. Vào tab **Actions** trên GitHub repo của bạn.
2. Chọn workflow **Market Radar Scheduled Update** ở danh sách bên trái.
3. Nhấn **Run workflow** -> Chọn branch `main` -> Nhấn nút xanh **Run workflow**.
4. GitHub Actions sẽ chạy toàn bộ pipeline, tính toán nến mới, nén DB, upload lên Release và kích hoạt Render reload ngay trước mắt bạn!
