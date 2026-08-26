import plotly.express as px
import streamlit as st

from src.data_loader import load_orders_full

st.set_page_config(page_title="Delivery Performance", page_icon="🚚", layout="wide")
st.title("🚚 Delivery Performance")

BLUE = "#2a78d6"
RED = "#e34948"

df = load_orders_full()
delivered = df[df["order_status"] == "delivered"].dropna(subset=["delivery_days", "delay_days"])

col1, col2, col3 = st.columns(3)
col1.metric("Avg. delivery time (days)", f"{delivered['delivery_days'].mean():.1f}")
col2.metric("Late deliveries", f"{delivered['is_late'].mean() * 100:.1f}%")
col3.metric("Avg. delay when late (days)", f"{delivered.loc[delivered['is_late'], 'delay_days'].mean():.1f}")

col1, col2 = st.columns(2)
with col1:
    mean_days = delivered["delivery_days"].mean()
    fig_hist = px.histogram(
        delivered,
        x="delivery_days",
        nbins=40,
        title="Distribution of delivery time (days)",
        labels={"delivery_days": "Delivery time (days)"},
    )
    fig_hist.update_traces(marker_color=BLUE)
    fig_hist.add_vline(
        x=mean_days,
        line_color="#898781",
        annotation_text=f"mean: {mean_days:.1f} days",
        annotation_position="top",
    )
    # 99% of deliveries land under ~45 days; without capping the range, the ~1%
    # tail stretching to 209 days squeezes the entire meaningful distribution
    # into a sliver on the left.
    p99 = delivered["delivery_days"].quantile(0.99)
    fig_hist.update_xaxes(range=[0, p99])
    st.plotly_chart(fig_hist, width="stretch")
with col2:
    by_state = (
        delivered.groupby("customer_state", as_index=False)["is_late"]
        .mean()
        .sort_values("is_late", ascending=False)
    )
    worst5 = set(by_state.head(5)["customer_state"])
    by_state["pct"] = by_state["is_late"] * 100
    by_state["label"] = by_state.apply(
        lambda r: f"{r['pct']:.0f}%" if r["customer_state"] in worst5 else "", axis=1
    )
    fig_state = px.bar(
        by_state,
        x="customer_state",
        y="pct",
        title="Late delivery rate by customer state (worst 5 labeled)",
        labels={"pct": "Late deliveries (%)", "customer_state": ""},
        text="label",
    )
    fig_state.update_traces(marker_color=BLUE, textposition="outside")
    st.plotly_chart(fig_state, width="stretch")

st.subheader("Delivery delay vs. review score")
st.caption(
    "Delay is measured against the estimated delivery date - negative means the order "
    "arrived earlier than promised. Every score arrives early on average, but the "
    "gap widens sharply for higher scores: earlier delivery tracks with happier customers."
)
by_score = delivered.groupby("review_score", as_index=False)["delay_days"].mean()
by_score["color"] = by_score["delay_days"].apply(lambda v: RED if v > 0 else BLUE)
fig_score = px.bar(
    by_score,
    x="review_score",
    y="delay_days",
    title="Avg. delivery delay by review score (negative = early)",
    labels={"delay_days": "Avg. delay (days)", "review_score": "Review score"},
    text=by_score["delay_days"].map(lambda v: f"{v:+.1f}d"),
)
fig_score.update_traces(marker_color=by_score["color"], textposition="outside")
fig_score.add_hline(y=0, line_color="#898781")
st.plotly_chart(fig_score, width="stretch")
