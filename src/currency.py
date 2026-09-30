# Approx. average BRL-per-USD rate over the order period (Sep 2016 - Oct 2018):
# yearly averages were 3.48 (2016), 3.19 (2017), 3.67 (2018) per exchange-rates.org.
# A single fixed rate is a simplification — it does not reflect day-to-day FX
# movement, only a rough R$-to-$ scale for display purposes.
USD_BRL_RATE = 3.5


def get_currency() -> tuple[str, float]:
    """Fixed USD display. Returns (symbol, divisor) to convert a BRL amount."""
    return "$", USD_BRL_RATE


def fmt_money(brl: float, decimals: int = 0) -> str:
    """Format a BRL amount in the display currency, e.g. 16_008_872 -> "$4,573,963"."""
    symbol, rate = get_currency()
    return f"{symbol}{brl / rate:,.{decimals}f}"


def fmt_money_short(brl: float) -> str:
    """Compact form for findings text, e.g. 16_008_872 -> "$4.57M"."""
    symbol, rate = get_currency()
    value = brl / rate
    for divisor, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= divisor:
            return f"{symbol}{value / divisor:.2f}{suffix}"
    return f"{symbol}{value:,.0f}"
