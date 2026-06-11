TAX_RATES = {
    "US": 0.08,
    "EU": 0.20,
    "UK": 0.20,
    "JP": 0.10,
}

REGION_TO_CURRENCY = {
    "US": "USD",
    "EU": "EUR",
    "UK": "GBP",
    "JP": "JPY",
}


def calculate_total(prices: list[float], region: str = "US") -> float:
    if not prices:
        raise ValueError("Price list cannot be empty")

    region = region.upper()
    if region not in TAX_RATES:
        raise KeyError(f"Unknown region: {region}")

    subtotal = sum(prices)
    tax_rate = TAX_RATES[region]
    return round(subtotal * (1 + tax_rate), 2)


def apply_discount(total: float, discount_percent: float = 0) -> float:
    if discount_percent < 0:
        discount_percent = 0
    if discount_percent > 100:
        discount_percent = 100
    return round(total * (1 - discount_percent / 100), 2)
