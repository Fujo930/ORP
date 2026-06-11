from .calculator import REGION_TO_CURRENCY


def format_currency(amount: float, region: str = "US") -> str:
    symbols = {
        "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3", "JPY": "\u00a5",
    }
    currency = REGION_TO_CURRENCY.get(region.upper(), region)
    sym = symbols.get(currency, currency)
    return f"{sym}{amount:.2f}"
