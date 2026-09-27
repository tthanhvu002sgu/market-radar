#!/usr/bin/env bash
set -e

echo "=== [1/2] Đồng bộ dữ liệu Market Radar từ GitHub Releases ==="
python scripts/sync_release_db.py --download

echo "=== [2/2] Khởi động Streamlit Server trên Render ==="
PORT="${PORT:-8501}"
echo "Server listening on port: $PORT"

exec streamlit run app/main.py \
    --server.port "$PORT" \
    --server.address "0.0.0.0" \
    --server.headless true \
    --browser.gatherUsageStats false
