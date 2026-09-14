from datetime import datetime, date
from typing import Any, Dict, List, Optional
import pandas as pd

def format_percentage(val: Optional[float]) -> str:
    if val is None or pd.isna(val):
        return "N/A"
    return f"{round(val * 100.0, 1)}%"

def format_currency(val: Optional[float]) -> str:
    if val is None or pd.isna(val):
        return "N/A"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}${round(abs_val / 1e12, 2)}T"
    elif abs_val >= 1e9:
        return f"{sign}${round(abs_val / 1e9, 2)}B"
    elif abs_val >= 1e6:
        return f"{sign}${round(abs_val / 1e6, 2)}M"
    return f"{sign}${round(abs_val, 2)}"

def calculate_days_to_earnings(earnings_date_str: Optional[str], ref_date: Optional[Any] = None) -> Optional[int]:
    """Calculate days from reference date (default today) to next earnings date."""
    if not earnings_date_str or earnings_date_str in ("Chưa xác minh", "N/A", "None"):
        return None
    try:
        # Normalize date string e.g. "2026-10-15 00:00:00" -> "2026-10-15"
        clean_str = str(earnings_date_str).split()[0].strip()
        parsed_date = datetime.strptime(clean_str, "%Y-%m-%d").date()
        if isinstance(ref_date, str):
            current_date = datetime.strptime(ref_date.split()[0].strip(), "%Y-%m-%d").date()
        elif isinstance(ref_date, datetime):
            current_date = ref_date.date()
        elif isinstance(ref_date, date):
            current_date = ref_date
        else:
            current_date = date.today()
        return (parsed_date - current_date).days
    except Exception:
        return None

def evaluate_fa_flags(symbol: str, fa_row: Optional[Dict[str, Any]] = None, ref_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Evaluate fundamental health, generate flags, and provide banking/financial-aware annotations.
    Includes days_to_earnings and event risk warnings [D-07].
    """
    if not fa_row or not isinstance(fa_row, dict):
        return {
            "has_data": False,
            "summary": "Chưa có dữ liệu FA được lưu cho mã này.",
            "flags": ["FA: Chưa có dữ liệu"],
            "earnings_status": "Chưa xác minh",
            "days_to_earnings": None,
            "is_financial": False,
            "metrics": {}
        }

    is_financial = bool(fa_row.get("is_financial", False))
    rev_growth = fa_row.get("revenue_growth")
    eps_growth = fa_row.get("earnings_growth")
    profit_margin = fa_row.get("profit_margins")
    op_margin = fa_row.get("operating_margins")
    cashflow = fa_row.get("operating_cashflow")
    debt = fa_row.get("total_debt")
    next_earnings = fa_row.get("next_earnings_date") or "Chưa xác minh"
    period_end = fa_row.get("period_end")
    fiscal_period = fa_row.get("fiscal_period")
    period_type = fa_row.get("period_type") or "Chỉ số tổng hợp Yahoo (YoY)"
    currency = fa_row.get("currency") or "USD"
    reported_date = fa_row.get("reported_date")
    retrieved_at = fa_row.get("retrieved_at")
    source = fa_row.get("source") or "Yahoo Finance (Số liệu tổng hợp / Aggregate)"
    data_status = fa_row.get("data_status") or "valid"
    sec_filing_url = fa_row.get("sec_filing_url") or f"https://www.sec.gov/edgar/browse/?CIK={symbol}"

    flags: List[str] = []

    # Calculate days to earnings
    days_to_earnings = calculate_days_to_earnings(next_earnings, ref_date=ref_date)
    is_imminent_earnings = False
    if days_to_earnings is not None:
        if 0 <= days_to_earnings <= 14:
            is_imminent_earnings = True
            flags.append(f"⚠️ RỦI RO BÁO CÁO TÀI CHÍNH: Sắp công bố Earnings trong {days_to_earnings} ngày ({next_earnings}) — rủi ro biến động gap giá cao!")
        elif days_to_earnings > 14:
            flags.append(f"Kỳ công bố Earnings dự kiến: {next_earnings} (còn {days_to_earnings} ngày)")
        else:
            flags.append(f"Kỳ công bố Earnings gần nhất: {next_earnings} (đang chờ cập nhật lịch mới)")
    else:
        if next_earnings and next_earnings != "Chưa xác minh":
            flags.append(f"Kỳ công bố Earnings dự kiến: {next_earnings}")
        else:
            flags.append("Earnings: Lịch chưa xác minh (cần kiểm tra trước khi swing)")

    # Provenance / Period context [R-02]
    period_ctx = f", {fiscal_period}" if fiscal_period and fiscal_period != "Chưa xác định kỳ" else ""
    src_ctx = f", nguồn {source}" if source else ""

    # Revenue & EPS Growth flags with baseline comparison
    if rev_growth is not None and not pd.isna(rev_growth):
        if rev_growth > 0.15:
            flags.append(f"Tăng trưởng doanh thu cao (+{format_percentage(rev_growth)} YoY{period_ctx}{src_ctx})")
        elif rev_growth < 0:
            flags.append(f"Cảnh báo: Doanh thu suy giảm ({format_percentage(rev_growth)} YoY{period_ctx})")

    if eps_growth is not None and not pd.isna(eps_growth):
        if eps_growth > 0.20:
            flags.append(f"Tăng trưởng EPS ấn tượng (+{format_percentage(eps_growth)} YoY{period_ctx}{src_ctx})")
        elif eps_growth < 0:
            flags.append(f"Cảnh báo: Lợi nhuận suy giảm ({format_percentage(eps_growth)} YoY{period_ctx})")

    # Profitability flags
    if profit_margin is not None and not pd.isna(profit_margin):
        if profit_margin < 0:
            flags.append("Cảnh báo: Doanh nghiệp đang lỗ ròng")

    # Financial / Banking specific handling for Debt and Cashflow
    has_debt_crisis = False
    if is_financial:
        flags.append("Định chế tài chính/Ngân hàng: Bỏ qua tỷ số đòn bẩy & FCF thông thường (cơ cấu vốn đặc thù)")
    else:
        if debt is not None and cashflow is not None and not pd.isna(debt) and not pd.isna(cashflow):
            if cashflow <= 0 and debt > 0:
                has_debt_crisis = True
                flags.append("Cảnh báo rủi ro: Dòng tiền hoạt động âm và có nợ vay")
            elif debt > 0 and cashflow > 0 and (debt / cashflow) > 5.0:
                flags.append(f"Đòn bẩy nợ cao: Tỷ lệ Nợ/Dòng tiền = {round(debt/cashflow, 1)}x")

    # Stale FA check (kỳ BCTC cũ > 180 ngày so với ref_date) [R-02 / Acceptance: FA tốt nhưng kỳ cũ]
    is_stale_fa = False
    ref_dt_val = period_end or reported_date
    if ref_dt_val and ref_dt_val not in ("Chưa xác minh", "N/A", "None"):
        try:
            rep_clean = str(ref_dt_val).split()[0].strip()
            rep_dt = datetime.strptime(rep_clean, "%Y-%m-%d").date()
            if isinstance(ref_date, str):
                cur_ref = datetime.strptime(ref_date.split()[0].strip(), "%Y-%m-%d").date()
            elif isinstance(ref_date, datetime):
                cur_ref = ref_date.date()
            elif isinstance(ref_date, date):
                cur_ref = ref_date
            else:
                cur_ref = date.today()

            age_days = (cur_ref - rep_dt).days
            if age_days > 180:
                is_stale_fa = True
                data_status = "stale"
                flags.append(f"⚠️ BCTC đã cũ (Stale): Số liệu từ kỳ kết thúc {rep_clean} ({age_days} ngày trước, > 6 tháng); cần đối chiếu hồ sơ mới nhất.")
        except Exception:
            pass

    # Unverified / Stale flag
    if not fiscal_period or fiscal_period == "Chưa xác định kỳ" or data_status == "partial":
        flags.append("Thông tin FA: Chưa xác minh kỳ cụ thể hoặc thiếu dữ liệu chi tiết")

    warning_level = "normal"
    if is_imminent_earnings or has_debt_crisis:
        warning_level = "high"
    elif is_stale_fa or (rev_growth is not None and rev_growth < 0) or (eps_growth is not None and eps_growth < 0) or (profit_margin is not None and profit_margin < 0):
        warning_level = "medium"

    return {
        "has_data": True,
        "is_financial": is_financial,
        "is_stale": is_stale_fa,
        "warning_level": warning_level,
        "earnings_status": next_earnings,
        "days_to_earnings": days_to_earnings,
        "period_end": period_end or "Chưa xác minh",
        "fiscal_period": fiscal_period or "Chưa xác minh kỳ",
        "period_type": period_type,
        "currency": currency,
        "reported_date": reported_date or "Chưa xác minh",
        "retrieved_at": retrieved_at or "N/A",
        "source": source,
        "data_status": data_status,
        "sec_filing_url": sec_filing_url,
        "flags": flags,
        "metrics": {
            "rev_growth_str": format_percentage(rev_growth),
            "eps_growth_str": format_percentage(eps_growth),
            "profit_margin_str": format_percentage(profit_margin),
            "op_margin_str": format_percentage(op_margin),
            "cashflow_str": format_currency(cashflow),
            "debt_str": format_currency(debt),
            "currency": currency,
            "period_end": period_end or "Chưa xác minh",
            "fiscal_period": fiscal_period or "Chưa xác minh kỳ",
            "period_type": period_type,
            "retrieved_at": retrieved_at or "N/A",
            "source": source,
            "sec_filing_url": sec_filing_url
        }
    }
