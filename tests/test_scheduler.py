import pytest
from datetime import datetime, date, time as dtime
from jobs.scheduler import parse_time_str, get_next_scheduled_run, DEFAULT_SCHEDULE_TIMES, format_duration


def test_parse_time_str():
    assert parse_time_str("05:00") == dtime(5, 0)
    assert parse_time_str("11:30") == dtime(11, 30)
    assert parse_time_str("23:00") == dtime(23, 0)
    assert parse_time_str("7") == dtime(7, 0)


def test_get_next_scheduled_run_same_day():
    # Gia su luc 09:15 sang -> moc tiep theo phai la 11:00 cung ngay
    ref = datetime(2026, 9, 12, 9, 15, 0)
    next_dt = get_next_scheduled_run(DEFAULT_SCHEDULE_TIMES, ref)
    assert next_dt == datetime(2026, 9, 12, 11, 0, 0)

    # Gia su luc 11:00:01 -> moc tiep theo phai la 17:00 cung ngay
    ref = datetime(2026, 9, 12, 11, 0, 1)
    next_dt = get_next_scheduled_run(DEFAULT_SCHEDULE_TIMES, ref)
    assert next_dt == datetime(2026, 9, 12, 17, 0, 0)


def test_get_next_scheduled_run_cross_midnight():
    # Gia su luc 23:30 dem -> moc tiep theo phai la 05:00 sang ngay mai
    ref = datetime(2026, 9, 12, 23, 30, 0)
    next_dt = get_next_scheduled_run(DEFAULT_SCHEDULE_TIMES, ref)
    assert next_dt == datetime(2026, 9, 13, 5, 0, 0)


def test_format_duration():
    assert format_duration(3665) == "1 giờ 1 phút 5 giây"
    assert format_duration(125) == "2 phút 5 giây"
    assert format_duration(45) == "45 giây"
