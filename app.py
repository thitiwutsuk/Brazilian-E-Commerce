import streamlit as st

from src.data_loader import load_orders_full

st.set_page_config(
    page_title="Olist E-Commerce Dashboard",
    page_icon="🛒",
    layout="wide",
)

st.title("🛒 Brazilian E-Commerce (Olist) Dashboard")
st.caption("Use the sidebar to navigate between analysis pages.")

df = load_orders_full()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Orders", f"{df['order_id'].nunique():,}")
col2.metric("Customers", f"{df['customer_unique_id'].nunique():,}")
col3.metric("Revenue (R$)", f"{df['payment_value'].sum():,.0f}")
col4.metric("Avg. review score", f"{df['review_score'].mean():.2f}")

st.divider()
st.subheader("Preview")
st.dataframe(df.head(20), width="stretch")
