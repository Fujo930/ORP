"""
Payment request validator.
Validates payment requests before processing.
"""

VALID_METHODS = {"credit_card", "paypal", "bank_transfer", "crypto"}


def validate_payment_request(data: dict) -> list[str]:
    """Validate a payment request dict.

    Returns a list of error messages (empty = valid).
    """
    errors = []

    if not data.get("method"):
        errors.append("Payment method is required")
    elif data["method"] not in VALID_METHODS:
        errors.append(f"Unknown method: {data['method']}")

    if not data.get("amount"):
        errors.append("Amount is required")
    elif not isinstance(data["amount"], (int, float)) or data["amount"] <= 0:
        errors.append("Amount must be a positive number")

    if not data.get("currency"):
        errors.append("Currency is required")

    return errors
