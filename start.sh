#!/usr/bin/env bash
set -e

echo "=== [1/3] Đồng bộ dữ liệu Market Radar từ GitHub Releases ==="
python scripts/sync_release_db.py --download

echo "=== [2/3] Đồng bộ lịch sử OFI (nếu có) ==="
python scripts/sync_release_db.py --download --ofi || true

echo "=== [3/3] Khởi động Streamlit Server trên Render ==="
PORT="${PORT:-8501}"
echo "Server listening on port: $PORT"

exec streamlit run app/main.py \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --browser.gatherUsageStats false
