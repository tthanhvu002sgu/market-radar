"""Sidebar order follows the review path; route IDs stay stable."""

DEFAULT_PAGE = "Thị trường"


def build_nav_sections(unread_count: int, candidate_count: int, base_count: int):
    return [
        {
            "category": "QUY TRÌNH RÀ SOÁT",
            "items": [
                ("Thị trường", "🌐 Thị trường"),
                ("Ngành", "📊 Ngành"),
                ("Nhóm ngành", "🗺️ Nhóm ngành"),
                ("Ứng viên", f"🎯 Ứng viên ({candidate_count})"),
                ("Nền giá & bứt phá", f"🧱 Nền giá & bứt phá ({base_count})"),
                ("Luồng rà soát", "🧭 Rà soát 6 bước"),
                ("Chất lượng tín hiệu", "📈 Chất lượng tín hiệu"),
            ],
        },
        {
            "category": "PHIÊN & SỰ KIỆN",
            "items": [
                ("Tổng hợp phiên", "📌 Tổng hợp phiên" + (f" ({unread_count})" if unread_count > 0 else "")),
                ("Lịch BCTC", "📅 Lịch BCTC"),
                ("Thay đổi giữa phiên", "🔄 Thay đổi giữa phiên"),
            ],
        },
        {
            "category": "HỆ THỐNG",
            "items": [("Dữ liệu & vận hành", "⚙️ Dữ liệu & vận hành")],
        },
    ]


def page_ids():
    return [page_id for section in build_nav_sections(0, 0, 0) for page_id, _ in section["items"]]


def resolve_initial_page(state):
    """Choose the market home once without overriding a later deliberate page choice."""
    active = state.get("active_page")
    if active not in page_ids() or (state.get("nav_home_version") != "market_v1" and active == "Tổng hợp phiên"):
        active = DEFAULT_PAGE
    state["active_page"] = active
    state["nav_home_version"] = "market_v1"
    return active
