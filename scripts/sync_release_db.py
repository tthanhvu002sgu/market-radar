"""
Market Radar - GitHub Release Database Synchronizer
Ho tro tai va giai nen file SQLite database (market_radar.db.gz) tu GitHub Release.
Hoat dong tot voi ca Public repo va Private repo (thong qua GITHUB_TOKEN).
"""

import argparse
import gzip
import json
import logging
import os
import shutil
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [sync_db]: %(message)s"
)
logger = logging.getLogger("sync_db")

DEFAULT_REPO = os.getenv("GITHUB_REPO", "tthanhvu002sgu/market-radar")
DEFAULT_TAG = os.getenv("RELEASE_TAG", "data-latest")
DEFAULT_ASSET = "market_radar.db.gz"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "market_radar.db"
GZ_PATH = DATA_DIR / DEFAULT_ASSET


def verify_sqlite_db(path: Path) -> bool:
    """Kiem tra tinh toan ven cua file SQLite sau khi giai nen."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        conn = sqlite3.connect(str(path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == "ok"
    except Exception as e:
        logger.error(f"Lỗi kiểm tra tính toàn vẹn SQLite: {e}")
        return False


def compress_db(source_db: Path = DB_PATH, target_gz: Path = GZ_PATH) -> bool:
    """Nen file SQLite database thanh file .gz de upload len GitHub Release."""
    if not source_db.exists():
        logger.error(f"Không tìm thấy file nguồn: {source_db}")
        return False
    
    logger.info(f"Đang nén {source_db} ({source_db.stat().st_size / 1024 / 1024:.2f} MB)...")
    target_gz.parent.mkdir(parents=True, exist_ok=True)
    with open(source_db, "rb") as f_in:
        with gzip.open(target_gz, "wb", compresslevel=9) as f_out:
            shutil.copyfileobj(f_in, f_out)
            
    logger.info(f"Nén hoàn tất! File kết quả: {target_gz} ({target_gz.stat().st_size / 1024 / 1024:.2f} MB).")
    return True


def download_from_release(
    repo: str = DEFAULT_REPO,
    tag: str = DEFAULT_TAG,
    asset_name: str = DEFAULT_ASSET,
    output_db: Path = DB_PATH,
    github_token: str = None
) -> bool:
    """Tải market_radar.db.gz từ GitHub Releases và giải nén thành market_radar.db."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    token = github_token or os.getenv("GITHUB_TOKEN", "").strip()

    # Thu muc tam
    temp_gz = DATA_DIR / f"{asset_name}.download"

    # URL truc tiep danh cho Public repo
    public_url = f"https://github.com/{repo}/releases/download/{tag}/{asset_name}"
    
    # 1. Thu tai qua Public URL truoc neu khong co Token
    download_success = False
    if not token:
        logger.info(f"Thử tải database từ Public Release: {public_url}")
        try:
            req = urllib.request.Request(
                public_url,
                headers={"User-Agent": "MarketRadar-Render-Sync/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp, open(temp_gz, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            download_success = True
            logger.info("Tải file từ Public URL thành công.")
        except Exception as e:
            logger.warning(f"Không thể tải từ Public URL ({e}). Sẽ thử qua GitHub API...")

    # 2. Neu chua tai duoc hoac co GITHUB_TOKEN (Private Repo hoac API)
    if not download_success:
        api_url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
        headers = {
            "User-Agent": "MarketRadar-Render-Sync/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
            logger.info(f"Đang gọi GitHub API (Private Repo với token) để lấy asset metadata: {api_url}")
        else:
            logger.info(f"Đang gọi GitHub API (Public) để lấy asset metadata: {api_url}")

        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                release_data = json.loads(resp.read().decode("utf-8"))
            
            asset_download_url = None
            for asset in release_data.get("assets", []):
                if asset.get("name") == asset_name:
                    asset_download_url = asset.get("url") if token else asset.get("browser_download_url")
                    break

            if not asset_download_url:
                logger.error(f"Không tìm thấy asset '{asset_name}' trong release tag '{tag}'!")
                return False

            logger.info(f"Bắt đầu tải asset: {asset_name}...")
            dl_headers = {"User-Agent": "MarketRadar-Render-Sync/1.0"}
            if token:
                dl_headers["Authorization"] = f"Bearer {token}"
                dl_headers["Accept"] = "application/octet-stream"

            dl_req = urllib.request.Request(asset_download_url, headers=dl_headers)
            with urllib.request.urlopen(dl_req, timeout=120) as resp, open(temp_gz, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            download_success = True
            logger.info("Tải asset thành công.")
        except Exception as e:
            logger.error(f"Lỗi khi tải asset từ GitHub API: {e}")
            if temp_gz.exists():
                temp_gz.unlink(missing_ok=True)
            return False

    # 3. Giai nen file .gz thanh .db
    if download_success and temp_gz.exists():
        temp_db = DATA_DIR / "market_radar.db.unpack"
        logger.info(f"Đang giải nén {temp_gz} ({temp_gz.stat().st_size / 1024 / 1024:.2f} MB)...")
        try:
            with gzip.open(temp_gz, "rb") as f_in, open(temp_db, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            
            # Kiem tra tinh toan ven
            if verify_sqlite_db(temp_db):
                # Thay the an toan
                if output_db.exists():
                    backup_path = output_db.with_suffix(".db.old")
                    output_db.replace(backup_path)
                temp_db.replace(output_db)
                logger.info(f"Đã cập nhật database thành công vào: {output_db} ({output_db.stat().st_size / 1024 / 1024:.2f} MB)")
                temp_gz.unlink(missing_ok=True)
                return True
            else:
                logger.error("File database sau khi giải nén không vượt qua kiểm tra SQLite integrity check!")
                if temp_db.exists():
                    temp_db.unlink(missing_ok=True)
                return False
        except Exception as e:
            logger.error(f"Lỗi khi giải nén file database: {e}")
            return False

    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Radar DB Sync Utility")
    parser.add_argument("--compress", action="store_true", help="Nén market_radar.db thành market_radar.db.gz")
    parser.add_argument("--download", action="store_true", help="Tải market_radar.db.gz từ GitHub Releases và giải nén")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub repository (VD: owner/repo)")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Release tag (VD: data-latest)")
    parser.add_argument("--token", default=None, help="GitHub Personal Access Token nếu repo là private")
    args = parser.parse_args()

    if args.compress:
        success = compress_db()
        sys.exit(0 if success else 1)
    elif args.download:
        success = download_from_release(repo=args.repo, tag=args.tag, github_token=args.token)
        if not success:
            if not DB_PATH.exists():
                logger.warning("Không tải được DB từ Release và chưa có DB cục bộ. Đang khởi tạo database rỗng...")
                from storage.database import init_db
                init_db()
            else:
                logger.info("Không tải được bản mới, tiếp tục sử dụng file database hiện có.")
        sys.exit(0)
    else:
        parser.print_help()
