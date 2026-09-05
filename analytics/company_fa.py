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

def evaluate_fa_flags(symbol: str, fa_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluate fundamental health, generate flags, and provide banking/financial-aware annotations.
    """
    if not fa_row or not isinstance(fa_row, dict):
        return {
            "has_data": False,
            "summary": "Chưa có dữ liệu FA được lưu cho mã này.",
            "flags": ["FA: Chưa có dữ liệu"],
            "earnings_status": "Chưa xác minh",
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

    flags: List[str] = []

    # Revenue & EPS Growth flags
    if rev_growth is not None and not pd.isna(rev_growth):
        if rev_growth > 0.15:
            flags.append(f"Tăng trưởng doanh thu cao (+{format_percentage(rev_growth)})")
        elif rev_growth < 0:
            flags.append(f"Cảnh báo: Doanh thu suy giảm ({format_percentage(rev_growth)})")

    if eps_growth is not None and not pd.isna(eps_growth):
        if eps_growth > 0.20:
            flags.append(f"Tăng trưởng EPS ấn tượng (+{format_percentage(eps_growth)})")
        elif eps_growth < 0:
            flags.append(f"Cảnh báo: Lợi nhuận suy giảm ({format_percentage(eps_growth)})")

    # Profitability flags
    if profit_margin is not None and not pd.isna(profit_margin):
        if profit_margin < 0:
            flags.append("Cảnh báo: Doanh nghiệp đang lỗ ròng")

    # Financial / Banking specific handling for Debt and Cashflow
    if is_financial:
        flags.append("Định chế tài chính/Ngân hàng: Bỏ qua tỷ số đòn bẩy & FCF thông thường (cơ cấu vốn đặc thù)")
    else:
        if debt is not None and cashflow is not None and not pd.isna(debt) and not pd.isna(cashflow):
            if cashflow <= 0 and debt > 0:
                flags.append("Cảnh báo rủi ro: Dòng tiền hoạt động âm và có nợ vay")
            elif debt > 0 and cashflow > 0 and (debt / cashflow) > 5.0:
                flags.append(f"Đòn bẩy nợ cao: Tỷ lệ Nợ/Dòng tiền = {round(debt/cashflow, 1)}x")

    # Earnings status flag
    if next_earnings and next_earnings != "Chưa xác minh":
        flags.append(f"Kỳ công bố Earnings dự kiến: {next_earnings}")
    else:
        flags.append("Earnings: Lịch chưa xác minh (cần kiểm tra trước khi swing)")

    return {
        "has_data": True,
        "is_financial": is_financial,
        "earnings_status": next_earnings,
        "flags": flags,
        "metrics": {
            "rev_growth_str": format_percentage(rev_growth),
            "eps_growth_str": format_percentage(eps_growth),
            "profit_margin_str": format_percentage(profit_margin),
            "op_margin_str": format_percentage(op_margin),
            "cashflow_str": format_currency(cashflow),
            "debt_str": format_currency(debt),
        }
    }
