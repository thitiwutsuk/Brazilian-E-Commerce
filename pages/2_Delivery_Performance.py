import plotly.express as px
import streamlit as st

from src.data_loader import load_orders_full

st.set_page_config(page_title="Delivery Performance", page_icon="🚚", layout="wide")
st.title("🚚 Delivery Performance")

df = load_orders_full()
delivered = df[df["order_status"] == "delivered"].dropna(subset=["delivery_days", "delay_days"])

col1, col2, col3 = st.columns(3)
col1.metric("Avg. delivery time (days)", f"{delivered['delivery_days'].mean():.1f}")
col2.metric("Late deliveries", f"{delivered['is_late'].mean() * 100:.1f}%")
col3.metric("Avg. delay when late (days)", f"{delivered.loc[delivered['is_late'], 'delay_days'].mean():.1f}")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(
        px.histogram(delivered, x="delivery_days", nbins=40, title="Distribution of delivery time (days)"),
        width="stretch",
    )
with col2:
    by_state = (
        delivered.groupby("customer_state", as_index=False)["is_late"]
        .mean()
        .sort_values("is_late", ascending=False)
    )
    st.plotly_chart(
        px.bar(by_state, x="customer_state", y="is_late", title="Late delivery rate by customer state"),
        width="stretch",
    )

st.subheader("Delivery delay vs. review score")
by_score = delivered.groupby("review_score", as_index=False)["delay_days"].mean()
st.plotly_chart(
    px.bar(by_score, x="review_score", y="delay_days", title="Avg. delay (days) by review score"),
    width="stretch",
)
