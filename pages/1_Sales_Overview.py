import plotly.express as px
import streamlit as st

from src.data_loader import load_orders_full

st.set_page_config(page_title="Sales Overview", page_icon="📈", layout="wide")
st.title("📈 Sales Overview")

df = load_orders_full()
delivered = df[df["order_status"] == "delivered"].copy()

by_month = (
    delivered.assign(month=delivered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
    .groupby("month", as_index=False)["payment_value"]
    .sum()
)
st.plotly_chart(
    px.line(by_month, x="month", y="payment_value", title="Revenue by month"),
    width="stretch",
)

col1, col2 = st.columns(2)

by_category = (
    delivered.groupby("product_category_name_english", as_index=False)["payment_value"]
    .sum()
    .sort_values("payment_value", ascending=False)
    .head(15)
)
with col1:
    st.plotly_chart(
        px.bar(
            by_category,
            x="payment_value",
            y="product_category_name_english",
            orientation="h",
            title="Top 15 categories by revenue",
        ).update_layout(yaxis={"categoryorder": "total ascending"}),
        width="stretch",
    )

by_state = (
    delivered.groupby("customer_state", as_index=False)["payment_value"]
    .sum()
    .sort_values("payment_value", ascending=False)
)
with col2:
    st.plotly_chart(
        px.bar(by_state, x="customer_state", y="payment_value", title="Revenue by customer state"),
        width="stretch",
    )
