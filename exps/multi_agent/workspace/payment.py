"""
Payment processing system.
Supports multiple payment methods: credit_card, paypal, bank_transfer, crypto
"""

import logging

# Known payment methods and their required fields
PAYMENT_METHODS = {
    "credit_card": {
        "required": ["card_number", "expiry", "cvv"],
        "fee_percent": 2.5,
    },
    "paypal": {
        "required": ["email"],
        "fee_percent": 3.0,
    },
    "bank_transfer": {
        "required": ["account_number", "routing_number"],
        "fee_percent": 0.5,
    },
    "crypto": {
        "required": ["wallet_address", "network"],
        "fee_percent": 1.0,
    },
}


def process_payment(method: str, amount: float, details: dict) -> dict:
    """Process a payment using the specified method.

    Args:
        method: Payment method key
        amount: Amount in dollars
        details: Payment details dict

    Returns:
        Result dict with status, transaction_id, fee

    Raises:
        ValueError: If method is unknown or missing required fields
    """
    if method not in PAYMENT_METHODS:
        raise ValueError(f"Unknown payment method: {method}")

    config = PAYMENT_METHODS[method]
    required = config["required"]

    # Validate required fields
    missing = [f for f in required if f not in details or not details[f]]
    if missing:
        raise ValueError(f"Missing required fields for {method}: {missing}")

    fee = round(amount * config["fee_percent"] / 100, 2)
    import uuid
    tx_id = f"tx_{uuid.uuid4().hex[:12]}"

    return {
        "status": "success",
        "transaction_id": tx_id,
        "amount": amount,
        "fee": fee,
        "method": method,
    }
