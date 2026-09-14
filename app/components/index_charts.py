"""
Index Charts Component (Cụm Biểu Đồ 3 Chỉ Số Lớn: S&P 500, NASDAQ, DOW).
Replicates the visual layout from Image 1:
- 3 cards side-by-side: S&P 500 (^GSPC), NASDAQ (^IXIC), DOW (^DJI)
- Session date, point change and percentage change (+/-)
- Yellow close price badge (e.g. 7656.98, 26333.0, 52573.3)
- Unified candlestick chart + relative volume meter side-by-side
- Previous close reference line (red dashed)
- Toggle between Intraday (5m) and Daily (30D) modes
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import yfinance as yf

INDEX_SPECS = [
    {
        "name": "S&P 500",
        "ticker": "^GSPC",
        "display_name": "S&P 500",
        "color": "#16A34A"
    },
    {
        "name": "NASDAQ",
        "ticker": "^IXIC",
        "display_name": "NASDAQ",
        "color": "#16A34A"
    },
    {
        "name": "DOW",
        "ticker": "^DJI",
        "display_name": "DOW",
        "color": "#16A34A"
    }
]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_index_intraday_data(ticker: str) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    """Fetch 1d 5m intraday data and previous close for an index ticker."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="5d", interval="5m")
        if df.empty:
            return None, None
        
        df.reset_index(inplace=True)
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df[date_col] = pd.to_datetime(df[date_col])
        
        latest_date = df[date_col].dt.date.max()
        df_latest = df[df[date_col].dt.date == latest_date].copy()
        
        df_prev = df[df[date_col].dt.date < latest_date]
        if not df_prev.empty:
            prev_close = float(df_prev["Close"].iloc[-1])
        else:
            info = getattr(t, "info", {}) or {}
            prev_close = float(info.get("previousClose") or df_latest["Open"].iloc[0])
            
        return df_latest, prev_close
    except Exception:
        return None, None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_index_daily_data(ticker: str) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
    """Fetch 1mo daily data and previous close for an index ticker."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1mo", interval="1d")
        if df.empty:
            return None, None
        
        df.reset_index(inplace=True)
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col])
        
        if len(df) >= 2:
            prev_close = float(df["Close"].iloc[-2])
        else:
            prev_close = float(df["Open"].iloc[0])
            
        return df, prev_close
    except Exception:
        return None, None

def render_html_safe(html_str: str):
    """Render HTML safely without markdown code block indentation issues."""
    if hasattr(st, "html"):
        st.html(html_str)
    else:
        import textwrap
        st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)

def create_unified_index_figure(
    df: pd.DataFrame,
    prev_close: Optional[float],
    rel_vol: float,
    is_intraday: bool = True
) -> go.Figure:
    """Generate a clean light-themed Plotly figure combining relative volume meter and candlesticks."""
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.09, 0.91],
        horizontal_spacing=0.03,
        shared_yaxes=False
    )

    # 1. Left Subplot: Relative Volume Indicator
    clamped_vol = min(max(rel_vol, 0.0), 2.0)
    fig.add_trace(
        go.Bar(
            x=["RVOL"],
            y=[clamped_vol],
            marker_color="#2563EB",
            width=0.45,
            showlegend=False,
            hoverinfo="y",
            name="Rel Vol"
        ),
        row=1,
        col=1
    )

    # 2. Right Subplot: Candlestick Chart
    date_col = "Datetime" if "Datetime" in df.columns else ("Date" if "Date" in df.columns else df.columns[0])
    fig.add_trace(
        go.Candlestick(
            x=df[date_col],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color="#16A34A",
            increasing_fillcolor="#22C55E",
            decreasing_line_color="#DC2626",
            decreasing_fillcolor="#EF4444",
            line=dict(width=1),
            showlegend=False,
            name="Nến"
        ),
        row=1,
        col=2
    )

    # Red dotted horizontal line for previous close
    if prev_close and prev_close > 0:
        fig.add_hline(
            y=prev_close,
            line_dash="dot",
            line_color="#DC2626",
            line_width=1.2,
            opacity=0.85,
            row=1,
            col=2
        )

    # Left Y-axis (Relative volume)
    fig.update_yaxes(
        range=[0, 2.0],
        tickvals=[0.5, 1.0, 1.5, 2.0],
        side="left",
        showgrid=False,
        tickfont=dict(size=10.5, color="#64748B", family="'Geist Mono', monospace"),
        title=dict(text="REL VOL", font=dict(size=10, color="#64748B", family="'Geist Mono', monospace")),
        row=1,
        col=1
    )
    fig.update_xaxes(showticklabels=False, showgrid=False, row=1, col=1)

    # Right Y-axis & X-axis (Candlestick chart)
    tick_fmt = "%-I%p" if is_intraday else "%b %d"
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        tickformat=tick_fmt,
        color="#64748B",
        rangeslider=dict(visible=False),
        tickfont=dict(size=11, color="#64748B", family="'Geist Mono', monospace"),
        row=1,
        col=2
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#F1F5F9",
        side="right",
        color="#64748B",
        tickfont=dict(size=11, color="#64748B", family="'Geist Mono', monospace"),
        row=1,
        col=2
    )

    fig.update_layout(
        template="plotly_white",
        height=205,
        margin=dict(l=0, r=36, t=8, b=16),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="'Geist', 'Inter', sans-serif"),
        hovermode="x unified"
    )
    return fig

def render_index_card(
    spec: Dict[str, str],
    is_intraday: bool = True
):
    """Render an individual index card in clean light theme with container border."""
    name = spec["name"]
    ticker = spec["ticker"]

    with st.container(border=True):
        if is_intraday:
            df, prev_close = fetch_index_intraday_data(ticker)
        else:
            df, prev_close = fetch_index_daily_data(ticker)

        if df is None or df.empty or prev_close is None:
            placeholder_html = (
                f'<div style="background: #FFFFFF; padding: 20px; color: #787774; min-height: 220px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-family: \'Geist\', \'Inter\', sans-serif;">'
                f'Đang tải dữ liệu {name}...'
                f'</div>'
            )
            render_html_safe(placeholder_html)
            return

        curr_close = float(df["Close"].iloc[-1])
        change_val = curr_close - prev_close
        change_pct = (change_val / prev_close) * 100.0 if prev_close > 0 else 0.0

        date_col = "Datetime" if "Datetime" in df.columns else ("Date" if "Date" in df.columns else df.columns[0])
        latest_ts = df[date_col].iloc[-1]
        if hasattr(latest_ts, "strftime"):
            date_str = latest_ts.strftime("%b %d")
        else:
            date_str = "Hôm nay"

        is_positive = (change_val >= 0)
        change_color = "#16A34A" if is_positive else "#DC2626"
        sign_str = "+" if is_positive else ""
        change_str = f"{sign_str}{change_val:.2f} ({sign_str}{change_pct:.2f}%)"

        rel_vol = 1.05
        if len(df) > 10:
            vol_mean = float(df["Volume"].tail(10).mean())
            if vol_mean > 0:
                rel_vol = round(float(df["Volume"].iloc[-1]) / vol_mean, 2)
        rel_vol = min(max(rel_vol, 0.4), 2.0)

        if curr_close >= 1000:
            curr_price_str = f"{curr_close:,.1f}"
        else:
            curr_price_str = f"{curr_close:,.2f}"

        header_html = (
            f'<div style="display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 6px; border-bottom: 1px solid #F1F5F9; margin-bottom: 4px;">'
            f'<div style="display: flex; align-items: baseline; gap: 8px;">'
            f'<span style="font-family: \'Geist\', \'Inter\', sans-serif; font-size: 20px; font-weight: 700; color: #111111; letter-spacing: -0.01em;">{name}</span>'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 12.5px; color: #64748B;">{date_str}</span>'
            f'</div>'
            f'<div style="display: flex; align-items: center; gap: 8px;">'
            f'<span style="font-family: \'Geist Mono\', monospace; font-size: 14px; font-weight: 600; color: {change_color};">{change_str}</span>'
            f'<span style="background: #FEF08A; color: #854D0E; border: 1px solid #FDE047; font-family: \'Geist Mono\', monospace; font-size: 13px; font-weight: 700; padding: 2px 7px; border-radius: 4px;">{curr_price_str}</span>'
            f'</div>'
            f'</div>'
        )
        render_html_safe(header_html)

        fig = create_unified_index_figure(df, prev_close, rel_vol=rel_vol, is_intraday=is_intraday)
        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"chart_index_{name}_{is_intraday}",
            config={"displayModeBar": False}
        )

def render_major_indices_section():
    """Render the top major indices section (S&P 500, NASDAQ, DOW)."""
    top_c1, top_c2 = st.columns([7, 3])
    with top_c1:
        st.markdown('<div class="editorial-hero" style="font-size: 22px; margin-bottom: 3px;">Chỉ Số Lớn Thị Trường Mỹ (Major Indices)</div>', unsafe_allow_html=True)
        st.markdown('<div class="editorial-sub" style="font-size: 14.5px; margin-bottom: 14px;">Biến động giá, đường tham chiếu phiên trước và thanh khoản tương đối của 3 chỉ số đầu tàu.</div>', unsafe_allow_html=True)
    with top_c2:
        mode_choice = st.radio(
            "Khung thời gian:",
            ["Intraday (5m)", "Daily (30D)"],
            horizontal=True,
            label_visibility="collapsed",
            key="index_chart_timeframe"
        )
    is_intraday = (mode_choice == "Intraday (5m)")

    col1, col2, col3 = st.columns(3)
    with col1:
        render_index_card(INDEX_SPECS[0], is_intraday=is_intraday)
    with col2:
        render_index_card(INDEX_SPECS[1], is_intraday=is_intraday)
    with col3:
        render_index_card(INDEX_SPECS[2], is_intraday=is_intraday)
