from mylib.calculator import calculate_total, apply_discount
import pytest


def test_calculate_total():
    assert calculate_total([10, 20], "US") == 32.40
    assert calculate_total([100], "EU") == 120.00


def test_empty_price_list():
    with pytest.raises(ValueError):
        calculate_total([], "US")


def test_case_insensitive():
    assert calculate_total([10], "us") == 10.80
    assert calculate_total([10], "Us") == 10.80
    assert calculate_total([10], "uS") == 10.80


def test_unknown_region():
    with pytest.raises(KeyError):
        calculate_total([10], "XX")


def test_apply_discount():
    assert apply_discount(100, 10) == 90.00
    assert apply_discount(100, 0) == 100.00


def test_discount_clamping():
    assert apply_discount(100, -50) == 100.00
    assert apply_discount(100, 150) == 0.00
    assert apply_discount(100, 200) == 0.00
