import streamlit as st

from src.data_loader import load_item_level, load_order_level
from src.sections import customers, delivery, modeling, quality, sales, schema, summary
from src.theme import configure_page

configure_page("Olist E-Commerce Report")
st.title("Brazilian E-Commerce (Olist): Analytical Report")

# Warm the cache once so every tab reads the same prepared tables.
load_order_level()
load_item_level()

SECTIONS = [
    ("Summary", summary),
    ("1. Data Schema", schema),
    ("2. Data Quality", quality),
    ("3. Cleaning & Modeling", modeling),
    ("4. Sales", sales),
    ("5. Delivery & Satisfaction", delivery),
    ("6. Customers & Geography", customers),
]

for tab, (_, section) in zip(st.tabs([name for name, _ in SECTIONS]), SECTIONS):
    with tab:
        section.render()
