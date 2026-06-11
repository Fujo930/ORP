from mylib.formatter import format_currency


def test_format_us():
    assert format_currency(10.80, "US") == "$10.80"


def test_format_eu():
    assert format_currency(120.00, "EU") == "\u20ac120.00"


def test_format_jp():
    assert format_currency(110.00, "JP") == "\u00a5110.00"


def test_cross_file_consistency():
    from mylib.calculator import REGION_TO_CURRENCY
    from mylib.formatter import format_currency
    total = 100 * 1.10  # 110 JPY
    formatted = format_currency(total, "JP")
    assert "\u00a5" in formatted
    assert REGION_TO_CURRENCY["JP"] == "JPY"
