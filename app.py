import streamlit as st

from src.currency import get_currency
from src.data_loader import load_orders_full
from src.theme import configure_page

configure_page("Olist E-Commerce Dashboard")

st.title("Brazilian E-Commerce (Olist) Dashboard")
st.caption("Use the sidebar to navigate between analysis pages.")

symbol, rate = get_currency()
df = load_orders_full()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Orders", f"{df['order_id'].nunique():,}")
col2.metric("Customers", f"{df['customer_unique_id'].nunique():,}")
col3.metric(f"Revenue ({symbol})", f"{df['payment_value'].sum() / rate:,.0f}")
col4.metric("Avg. review score", f"{df['review_score'].mean():.2f}")
