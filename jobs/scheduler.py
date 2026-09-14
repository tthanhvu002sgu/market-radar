"""
Market Radar - Standard Schedule Background Runner
Tu dong chay pipeline cap nhat du lieu thi truong theo cac moc gio chuan co dinh:
Mac dinh moi 6 tieng: 05:00, 11:00, 17:00, 23:00 (gio he thong / Viet Nam).
"""

import argparse
import logging
import sys
import time
from datetime import datetime, time as dtime, timedelta
from typing import List, Optional

from storage.repository import MarketRadarRepository
from jobs.update_pipeline import run_update_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [scheduler]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("scheduler")

# Cac moc gio chuan mac dinh (cach deu moi 6 tieng)
DEFAULT_SCHEDULE_TIMES = ["05:00", "11:00", "17:00", "23:00"]


def parse_time_str(t_str: str) -> dtime:
    """Parse chuoi 'HH:MM' thanh datetime.time object."""
    parts = t_str.strip().split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return dtime(hour=hour, minute=minute)


def get_next_scheduled_run(schedule_times: List[str], ref_dt: Optional[datetime] = None) -> datetime:
    """
    Xac dinh thoi diem chay ke tiep gan nhat dua tren danh sach cac moc gio chuan.
    Neu tat ca moc gio trong ngay da qua, chuyen sang moc dau tien cua ngay mai.
    """
    now = ref_dt or datetime.now()
    parsed_times = sorted([parse_time_str(t) for t in schedule_times])

    # Tim moc gio tiep theo trong ngay hom nay
    for t in parsed_times:
        candidate = datetime.combine(now.date(), t)
        if candidate > now:
            return candidate

    # Neu da qua het cac moc trong ngay, lay moc dau tien cua ngay mai
    tomorrow = now.date() + timedelta(days=1)
    return datetime.combine(tomorrow, parsed_times[0])


def format_duration(seconds: float) -> str:
    """Dinh dang so giay thanh chuoi Gio:Phut:Giay de doc."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    parts = []
    if hrs > 0:
        parts.append(f"{hrs} giờ")
    if mins > 0:
        parts.append(f"{mins} phút")
    parts.append(f"{secs} giây")
    return " ".join(parts)


def start_standard_scheduler(
    schedule_times: Optional[List[str]] = None,
    run_immediately: bool = True
):
    if not schedule_times:
        schedule_times = DEFAULT_SCHEDULE_TIMES

    times_str = ", ".join(sorted(schedule_times))
    logger.info("=" * 65)
    logger.info("  MARKET RADAR - BỘ LẬP LỊCH THEO KHUNG GIỜ CHUẨN")
    logger.info("=" * 65)
    logger.info(f"Các mốc giờ chạy tự động cố định: [{times_str}] (mỗi 6 tiếng)")
    logger.info("Ý nghĩa các mốc:")
    logger.info("  - 05:00: Chốt trọn vẹn nến EOD sau khi thị trường Mỹ đóng cửa.")
    logger.info("  - 11:00 & 17:00: Cập nhật bổ sung số liệu BCTC và chuẩn bị phiên tối.")
    logger.info("  - 23:00: Cập nhật định kỳ cuối ngày.")
    logger.info("Nhấn Ctrl + C bất kỳ lúc nào để dừng tiến trình an toàn.")
    logger.info("=" * 65)

    # 1. Chay khoi tao lan dau neu can
    if run_immediately:
        logger.info("Khởi chạy cập nhật snapshot ban đầu khi vừa bật hệ thống...")
        try:
            res = run_update_pipeline()
            if res.get("success"):
                logger.info(f"Hoàn thành khởi tạo! Snapshot #{res.get('snapshot_id')} ({res.get('as_of')}).")
            else:
                logger.warning(f"Thông báo từ pipeline: {res.get('message')}")
        except Exception as e:
            logger.error(f"Lỗi cập nhật khởi tạo: {e}", exc_info=True)
    else:
        logger.info("Bỏ qua cập nhật ban đầu, tiến trình sẽ chờ đến mốc giờ chuẩn tiếp theo.")

    # 2. Vong lap cho va thuc thi dung moc gio chuan
    cycle_count = 1
    while True:
        try:
            now = datetime.now()
            next_run = get_next_scheduled_run(schedule_times, now)
            wait_seconds = (next_run - now).total_seconds()

            logger.info("-" * 65)
            logger.info(
                f"Lần cập nhật #{cycle_count} kế tiếp: {next_run.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(còn {format_duration(wait_seconds)})."
            )
            logger.info("Tiến trình đang ở chế độ chờ (Sleep)...")

            # Vong lap ngu an toan theo tung khoang 15s de bat Ctrl+C va chong drift gio khi laptop sleep
            while datetime.now() < next_run:
                remaining = (next_run - datetime.now()).total_seconds()
                sleep_chunk = min(15.0, max(0.5, remaining))
                time.sleep(sleep_chunk)

            # Den gio chuan -> Thuc thi
            trigger_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"=== [MỐC CHUẨN #{cycle_count}] Bắt đầu chu kỳ cập nhật lúc {trigger_time_str} ===")
            
            res = run_update_pipeline()
            if res.get("success"):
                logger.info(
                    f"Cập nhật thành công! Snapshot #{res.get('snapshot_id')} "
                    f"({res.get('as_of')}) - Độ phủ: {res.get('coverage_pct', 0)*100:.1f}%. "
                    f"Số ứng viên: {res.get('total_candidates', 0)}."
                )
            else:
                logger.warning(f"Kết quả cập nhật: {res.get('message')}")

            cycle_count += 1

        except KeyboardInterrupt:
            logger.info("\nĐã nhận tín hiệu dừng (Ctrl + C). Thoát Market Radar Scheduler an toàn.")
            break
        except Exception as e:
            logger.error(f"Lỗi không mong muốn trong vòng lặp scheduler: {e}", exc_info=True)
            logger.info("Tiến trình sẽ thử lại sau 60 giây...")
            time.sleep(60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Market Radar Standard Schedule Background Runner")
    parser.add_argument(
        "-t", "--times",
        type=str,
        default="05:00,11:00,17:00,23:00",
        help="Danh sách các mốc giờ chạy phân tách bằng dấu phẩy (mặc định: '05:00,11:00,17:00,23:00')"
    )
    parser.add_argument(
        "--no-immediate",
        action="store_true",
        help="Không chạy ngay lập tức khi vừa bật, chờ tới đúng mốc giờ kế tiếp mới chạy"
    )

    args = parser.parse_args()
    times_list = [t.strip() for t in args.times.split(",") if t.strip()]
    start_standard_scheduler(schedule_times=times_list, run_immediately=not args.no_immediate)
