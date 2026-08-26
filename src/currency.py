import streamlit as st

# Approx. average BRL-per-USD rate over the order period (Sep 2016 - Oct 2018):
# yearly averages were 3.48 (2016), 3.19 (2017), 3.67 (2018) per exchange-rates.org.
# A single fixed rate is a simplification — it does not reflect day-to-day FX
# movement, only a rough R$-to-$ scale for display purposes.
USD_BRL_RATE = 3.5


def currency_selector() -> tuple[str, float]:
    """Sidebar currency toggle. Returns (symbol, divisor) to convert a BRL amount."""
    choice = st.sidebar.radio("Currency", ["R$ (BRL)", "$ (USD, approx.)"], key="currency")
    if choice.startswith("$"):
        return "$", USD_BRL_RATE
    return "R$", 1.0
