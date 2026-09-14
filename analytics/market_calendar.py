"""
US Equity Market Trading Calendar (NYSE / NASDAQ).
Handles standard holidays, observances, early closures (13:00 ET),
and trading session resolution without external paid dependencies.
"""
from datetime import date, datetime, time, timedelta
from typing import Any, List, Optional, Set, Tuple, Union
from zoneinfo import ZoneInfo

from config.settings import (
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    US_MARKET_TZ,
)

# Standard early close time: 13:00 ET
EARLY_CLOSE_HOUR = 13
EARLY_CLOSE_MINUTE = 0

def _get_easter_date(year: int) -> date:
    """Anonymous Gregorian algorithm to compute Western Easter Sunday."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)

def _get_good_friday(year: int) -> date:
    """Good Friday is 2 days before Easter Sunday."""
    easter = _get_easter_date(year)
    return easter - timedelta(days=2)

def _get_nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """Find the n-th weekday of a given month (0 = Monday, 6 = Sunday)."""
    count = 0
    d = date(year, month, 1)
    while d.month == month:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)
    raise ValueError(f"Could not find {n}-th weekday {weekday} in month {month}/{year}")

def _get_last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Find the last weekday of a given month (0 = Monday, 6 = Sunday)."""
    # Start from last day of month and go backwards
    if month == 12:
        d = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d

def _adjust_observed(d: date) -> Optional[date]:
    """
    US Holiday observation rule:
    If Saturday -> observed on preceding Friday.
    If Sunday -> observed on succeeding Monday.
    If weekday -> that date itself.
    """
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)
    return d

def get_market_holidays(year: int) -> Set[date]:
    """
    Return set of NYSE/NASDAQ official closed holiday dates for a given year.
    Includes:
    - New Year's Day (Jan 1, observed)
    - Martin Luther King Jr. Day (3rd Monday in Jan)
    - Washington's Birthday / Presidents' Day (3rd Monday in Feb)
    - Good Friday (2 days before Easter)
    - Memorial Day (Last Monday in May)
    - Juneteenth National Independence Day (June 19, observed, official since 2022)
    - Independence Day (July 4, observed)
    - Labor Day (1st Monday in Sep)
    - Thanksgiving Day (4th Thursday in Nov)
    - Christmas Day (Dec 25, observed)
    """
    holidays = set()

    # 1. New Year's Day
    # If Jan 1 is Sunday -> observed Monday Jan 2
    ny_day = date(year, 1, 1)
    if ny_day.weekday() == 6:  # Sunday -> Monday Jan 2
        holidays.add(date(year, 1, 2))
    elif ny_day.weekday() < 5:
        holidays.add(ny_day)

    # 2. Martin Luther King Jr. Day (3rd Mon of Jan)
    holidays.add(_get_nth_weekday_of_month(year, 1, 0, 3))

    # 3. Washington's Birthday (3rd Mon of Feb)
    holidays.add(_get_nth_weekday_of_month(year, 2, 0, 3))

    # 4. Good Friday
    holidays.add(_get_good_friday(year))

    # 5. Memorial Day (Last Mon of May)
    holidays.add(_get_last_weekday_of_month(year, 5, 0))

    # 6. Juneteenth (June 19, since 2022)
    if year >= 2022:
        june_19 = _adjust_observed(date(year, 6, 19))
        if june_19:
            holidays.add(june_19)

    # 7. Independence Day (July 4)
    july_4 = _adjust_observed(date(year, 7, 4))
    if july_4:
        holidays.add(july_4)

    # 8. Labor Day (1st Mon of Sep)
    holidays.add(_get_nth_weekday_of_month(year, 9, 0, 1))

    # 9. Thanksgiving Day (4th Thu of Nov)
    thanksgiving = _get_nth_weekday_of_month(year, 11, 3, 4)
    holidays.add(thanksgiving)

    # 10. Christmas Day (Dec 25)
    xmas = _adjust_observed(date(year, 12, 25))
    if xmas:
        holidays.add(xmas)

    return holidays

def get_early_close_dates(year: int) -> Set[date]:
    """
    Return set of dates when NYSE/NASDAQ closes early at 13:00 ET.
    - Day after Thanksgiving (Black Friday: 4th Friday in Nov)
    - Christmas Eve (Dec 24) if it falls on a weekday (and not a full holiday)
    - July 3rd (day before July 4) if July 4 falls on a weekday
    """
    early_dates = set()

    # Black Friday: day after Thanksgiving
    thanksgiving = _get_nth_weekday_of_month(year, 11, 3, 4)
    early_dates.add(thanksgiving + timedelta(days=1))

    # Christmas Eve (Dec 24)
    dec_24 = date(year, 12, 24)
    if dec_24.weekday() < 5:
        if date(year, 12, 25).weekday() != 5:
            early_dates.add(dec_24)

    # Day before July 4th
    july_3 = date(year, 7, 3)
    if july_3.weekday() < 5:
        if date(year, 7, 4).weekday() < 5:
            early_dates.add(july_3)

    return early_dates

_HOLIDAYS_CACHE = {}
_EARLY_CLOSE_CACHE = {}

def is_market_holiday(d: date) -> bool:
    """Check if date is a scheduled NYSE market holiday."""
    if d.weekday() >= 5:
        return True
    if d.year not in _HOLIDAYS_CACHE:
        _HOLIDAYS_CACHE[d.year] = get_market_holidays(d.year)
    return d in _HOLIDAYS_CACHE[d.year]

def is_early_close(d: date) -> bool:
    """Check if date has an early market close (13:00 ET)."""
    if d.weekday() >= 5 or is_market_holiday(d):
        return False
    if d.year not in _EARLY_CLOSE_CACHE:
        _EARLY_CLOSE_CACHE[d.year] = get_early_close_dates(d.year)
    return d in _EARLY_CLOSE_CACHE[d.year]

def get_market_close_time(d: date) -> time:
    """Return scheduled market close time in America/New_York (13:00 or 16:00 ET)."""
    if is_early_close(d):
        return time(EARLY_CLOSE_HOUR, EARLY_CLOSE_MINUTE)
    return time(MARKET_CLOSE_HOUR, MARKET_CLOSE_MINUTE)

def is_trading_day(d: date) -> bool:
    """Returns True if the date is a normal or early-close US equity trading day."""
    if d.weekday() >= 5:
        return False
    return not is_market_holiday(d)

def get_previous_trading_day(d: date) -> date:
    """Return the most recent trading day strictly before date d."""
    cur = d - timedelta(days=1)
    while not is_trading_day(cur):
        cur -= timedelta(days=1)
    return cur

def get_next_trading_day(d: date) -> date:
    """Return the next trading day strictly after date d."""
    cur = d + timedelta(days=1)
    while not is_trading_day(cur):
        cur += timedelta(days=1)
    return cur

def get_trading_days(start_date: date, end_date: date) -> List[date]:
    """Return list of trading days in [start_date, end_date] inclusive."""
    res = []
    cur = start_date
    while cur <= end_date:
        if is_trading_day(cur):
            res.append(cur)
        cur += timedelta(days=1)
    return res

def determine_trading_session(ref_time: Optional[datetime] = None) -> Tuple[str, bool]:
    """
    Determine the target closed US equity trading session in America/New_York.
    Takes into account weekdays, holidays, early closes (13:00 ET), and regular closes (16:00 ET).
    Returns:
        (target_session_str: YYYY-MM-DD, is_market_closed_today: bool)
    """
    tz = ZoneInfo(US_MARKET_TZ)
    now_et = ref_time.astimezone(tz) if (ref_time and ref_time.tzinfo) else (
        ref_time.replace(tzinfo=tz) if ref_time else datetime.now(tz)
    )
    today = now_et.date()

    if is_trading_day(today):
        close_t = get_market_close_time(today)
        if now_et.time() >= close_t:
            return today.strftime("%Y-%m-%d"), True
        else:
            prev = get_previous_trading_day(today)
            return prev.strftime("%Y-%m-%d"), False
    else:
        prev = get_previous_trading_day(today)
        return prev.strftime("%Y-%m-%d"), True

def is_end_of_trading_week(d: date) -> bool:
    """
    Check if date d is the last trading day of its calendar week.
    Usually Friday, but Thursday if Friday is Good Friday or Christmas.
    """
    if not is_trading_day(d):
        return False
    curr_weekday = d.weekday()
    for days_ahead in range(1, 7 - curr_weekday):
        next_day = d + timedelta(days=days_ahead)
        if is_trading_day(next_day):
            return False
    return True

def get_market_status_now(ref_time: Optional[datetime] = None) -> dict:
    """
    Real-time NYSE / NASDAQ market clock and trading status [D-05].
    Computes current time in ET (New York) and ICT (Vietnam), determining whether the
    market is in Pre-market, Regular Trading, After-hours, Closed Overnight, Holiday, or Weekend.
    """
    tz_et = ZoneInfo(US_MARKET_TZ)
    tz_ict = ZoneInfo("Asia/Ho_Chi_Minh")

    if ref_time and ref_time.tzinfo:
        now_et = ref_time.astimezone(tz_et)
        now_ict = ref_time.astimezone(tz_ict)
    elif ref_time:
        now_et = ref_time.replace(tzinfo=tz_et)
        now_ict = now_et.astimezone(tz_ict)
    else:
        now_et = datetime.now(tz_et)
        now_ict = datetime.now(tz_ict)

    today = now_et.date()
    target_session, is_market_closed_today = determine_trading_session(ref_time)

    if today.weekday() >= 5:
        is_open = False
        status_phase = "weekend"
        status_badge = "Đóng cửa (Cuối tuần)"
        status_badge_color = "#787774"
        detail = "Thị trường Mỹ nghỉ giao dịch cuối tuần (Thứ Bảy - Chủ Nhật)."
    elif is_market_holiday(today):
        is_open = False
        status_phase = "holiday"
        status_badge = "Đóng cửa (Nghỉ lễ NYSE)"
        status_badge_color = "#9F2F2D"
        detail = f"Hôm nay là ngày nghỉ lễ chính thức của thị trường chứng khoán Mỹ ({today.strftime('%Y-%m-%d')})."
    else:
        close_t = get_market_close_time(today)
        open_t = time(9, 30)
        pre_t = time(4, 0)
        after_t = time(20, 0) if close_t.hour == 16 else time(17, 0)
        curr_t = now_et.time()

        if curr_t < pre_t:
            is_open = False
            status_phase = "closed_night"
            status_badge = "Đóng cửa qua đêm"
            status_badge_color = "#787774"
            detail = f"Phiên chính thức sẽ bắt đầu lúc 09:30 ET ({open_t.strftime('%H:%M')} ET)."
        elif pre_t <= curr_t < open_t:
            is_open = False
            status_phase = "pre_market"
            status_badge = "Tiền phiên (Pre-Market)"
            status_badge_color = "#8F6B00"
            detail = "Giao dịch trước giờ mở cửa (04:00 - 09:30 ET). Thanh khoản thấp hơn phiên chính."
        elif open_t <= curr_t < close_t:
            is_open = True
            status_phase = "regular"
            status_badge = "Đang giao dịch (Regular Trading)"
            status_badge_color = "#346538"
            early_txt = " (Đóng cửa sớm 13:00 ET)" if is_early_close(today) else ""
            detail = f"Phiên giao dịch chính thức đang diễn ra{early_txt}."
        elif close_t <= curr_t < after_t:
            is_open = False
            status_phase = "after_hours"
            status_badge = "Sau phiên (After-Hours)"
            status_badge_color = "#8F6B00"
            detail = f"Phiên chính thức đã kết thúc lúc {close_t.strftime('%H:%M')} ET. Đang trong giờ sau phiên."
        else:
            is_open = False
            status_phase = "closed_night"
            status_badge = "Đã đóng cửa phiên"
            status_badge_color = "#787774"
            detail = f"Phiên giao dịch ngày {today.strftime('%Y-%m-%d')} đã kết thúc toàn diện."

    return {
        "now_et": now_et,
        "now_ict": now_ict,
        "et_str": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
        "ict_str": now_ict.strftime("%Y-%m-%d %H:%M:%S ICT"),
        "is_open": is_open,
        "status_phase": status_phase,
        "status_badge": status_badge,
        "status_badge_color": status_badge_color,
        "status_detail": detail,
        "target_session": target_session,
        "is_early_close": is_early_close(today) if is_trading_day(today) else False,
        "close_time_str": get_market_close_time(today).strftime("%H:%M ET") if is_trading_day(today) else "16:00 ET"
    }

def compute_session_age(as_of: str, ref_time: Optional[datetime] = None, target_session: Optional[str] = None) -> dict:
    """
    Compute data snapshot freshness and session lag relative to current market state [D-05].
    Allows passing target_session directly or computing it from ref_time.
    """
    if target_session is None:
        market_status = get_market_status_now(ref_time)
        target_session = market_status["target_session"]

    try:
        as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
        target_date = datetime.strptime(target_session, "%Y-%m-%d").date()
    except Exception:
        return {
            "as_of": as_of,
            "target_session": target_session,
            "lag_sessions": 0,
            "is_latest": True,
            "is_stale": False,
            "freshness_label": "Chưa rõ",
            "freshness_badge_color": "#787774",
            "detail": f"Thời điểm {as_of}"
        }

    if as_of_date == target_date:
        return {
            "as_of": as_of,
            "target_session": target_session,
            "lag_sessions": 0,
            "is_latest": True,
            "is_stale": False,
            "freshness_label": "Mới nhất (Latest EOD)",
            "freshness_badge_color": "#346538",
            "detail": f"Dữ liệu phản ánh đúng phiên EOD gần nhất ({as_of})."
        }
    elif as_of_date < target_date:
        tds = get_trading_days(as_of_date + timedelta(days=1), target_date)
        lag = len(tds)
        color = "#9F2F2D" if lag > 1 else "#8F6B00"
        return {
            "as_of": as_of,
            "target_session": target_session,
            "lag_sessions": lag,
            "is_latest": False,
            "is_stale": (lag > 0),
            "freshness_label": f"Lạc hậu {lag} phiên (Lag)",
            "freshness_badge_color": color,
            "detail": f"Snapshot thuộc phiên {as_of}, chậm hơn phiên đóng cửa mục tiêu {target_session} ({lag} phiên giao dịch). Bấm 'Cập nhật dữ liệu ngay' để nạp phiên mới."
        }
    else:
        return {
            "as_of": as_of,
            "target_session": target_session,
            "lag_sessions": 0,
            "is_latest": True,
            "is_stale": False,
            "freshness_label": "Snapshot chỉ định",
            "freshness_badge_color": "#787774",
            "detail": f"Dữ liệu phiên {as_of}."
        }

def get_remaining_trading_sessions_in_week(d: Any) -> int:
    """
    Calculate number of remaining trading days in the current calendar week after date d.
    Correctly accounts for weekends and scheduled NYSE market holidays.
    Example:
    - Thursday with normal Friday: returns 1
    - Thursday before Good Friday (holiday): returns 0
    - Friday: returns 0
    """
    if isinstance(d, str):
        try:
            d = datetime.strptime(d.split()[0], "%Y-%m-%d").date()
        except Exception:
            return 0
    elif isinstance(d, datetime):
        d = d.date()

    # Find Friday of current week
    days_to_friday = 4 - d.weekday()
    if days_to_friday <= 0:
        return 0

    remaining = 0
    for offset in range(1, days_to_friday + 1):
        check_d = d + timedelta(days=offset)
        if is_trading_day(check_d):
            remaining += 1

    return remaining


