"""
Tests for payment processing system.
"""

from payment import process_payment, PAYMENT_METHODS
from validator import validate_payment_request


def test_credit_card():
    result = process_payment("credit_card", 100.0,
                             {"card_number": "4111", "expiry": "12/28", "cvv": "123"})
    assert result["status"] == "success"
    assert result["fee"] == 2.50


def test_paypal():
    result = process_payment("paypal", 50.0, {"email": "user@example.com"})
    assert result["status"] == "success"
    assert result["fee"] == 1.50


def test_bank_transfer():
    result = process_payment("bank_transfer", 200.0,
                             {"account_number": "12345", "routing_number": "021"})
    assert result["status"] == "success"
    assert result["fee"] == 1.00


def test_unknown_method():
    try:
        process_payment("crypto", 100.0, {})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_missing_fields():
    try:
        process_payment("credit_card", 100.0, {})
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_validator_credit_card():
    errors = validate_payment_request({
        "method": "credit_card", "amount": 50.0, "currency": "USD"
    })
    assert len(errors) == 0, f"Unexpected errors: {errors}"


def test_validator_bad_method():
    errors = validate_payment_request({
        "method": "bitcoin", "amount": 50.0, "currency": "USD"
    })
    assert len(errors) > 0


def test_validator_missing_amount():
    errors = validate_payment_request({
        "method": "credit_card", "currency": "USD"
    })
    assert len(errors) > 0
