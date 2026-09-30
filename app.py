import streamlit as st

from src.data_loader import load_item_level, load_order_level
from src.kpis import reporting_periods
from src.sections import appendix, customers, delivery, recommendations, sales, schema, summary
from src.theme import configure_page

configure_page("Olist Marketplace Performance Report")
st.title("Olist Marketplace Performance Report")
st.caption(f"Data Intelligence · Business review {reporting_periods()['label']}")

# Warm the cache once so every tab reads the same prepared tables.
load_order_level()
load_item_level()

SECTIONS = [
    ("Executive Summary", summary),
    ("Data Architecture", schema),
    ("Sales & Growth", sales),
    ("Customer Experience", delivery),
    ("Customers & Markets", customers),
    ("Recommendations", recommendations),
    ("Appendix: Data & Methodology", appendix),
]

for tab, (_, section) in zip(st.tabs([name for name, _ in SECTIONS]), SECTIONS):
    with tab:
        section.render()
