import plotly.express as px
import streamlit as st

from src.currency import currency_selector
from src.data_loader import load_orders_full
from src.theme import BRAND_COLOR, configure_page, style_fig

configure_page("Sales Overview", "📈")
st.title("📈 Sales Overview")

GREEN = BRAND_COLOR

symbol, rate = currency_selector()
df = load_orders_full()
delivered = df[df["order_status"] == "delivered"].copy()
delivered["revenue"] = delivered["payment_value"] / rate


def fmt(value: float) -> str:
    return f"{symbol}{value:,.0f}"


by_month = (
    delivered.assign(month=delivered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
    .groupby("month", as_index=False)["revenue"]
    .sum()
)
peak = by_month.loc[by_month["revenue"].idxmax()]

col1, col2, col3 = st.columns(3)
col1.metric("Total revenue", fmt(delivered["revenue"].sum()))
col2.metric("Peak month", peak["month"].strftime("%b %Y"), fmt(peak["revenue"]))
col3.metric("Avg. order value", fmt(delivered.groupby("order_id")["revenue"].sum().mean()))

fig_month = px.line(
    by_month,
    x="month",
    y="revenue",
    title="Revenue by month",
    labels={"revenue": f"Revenue ({symbol})", "month": ""},
    markers=True,
)
fig_month.update_traces(line_color=GREEN, marker_color=GREEN)
fig_month.add_scatter(
    x=[peak["month"]],
    y=[peak["revenue"]],
    mode="markers+text",
    text=[f"peak: {peak['month'].strftime('%b %Y')}"],
    textposition="top center",
    marker=dict(size=10, color=GREEN),
    showlegend=False,
)
st.plotly_chart(style_fig(fig_month), width="stretch")

col1, col2 = st.columns(2)

by_category = (
    delivered.groupby("product_category_name_english", as_index=False)["revenue"]
    .sum()
    .sort_values("revenue", ascending=False)
    .head(15)
)
with col1:
    fig_cat = px.bar(
        by_category,
        x="revenue",
        y="product_category_name_english",
        orientation="h",
        title="Top 15 categories by revenue",
        labels={"revenue": f"Revenue ({symbol})", "product_category_name_english": ""},
        text=by_category["revenue"].map(fmt),
    )
    fig_cat.update_traces(marker_color=GREEN, textposition="outside")
    fig_cat.update_layout(
        yaxis={"categoryorder": "total ascending", "automargin": True},
        xaxis_range=[0, by_category["revenue"].max() * 1.2],
    )
    st.plotly_chart(style_fig(fig_cat), width="stretch")

by_state = (
    delivered.groupby("customer_state", as_index=False)["revenue"]
    .sum()
    .sort_values("revenue", ascending=False)
)
top5_states = set(by_state.head(5)["customer_state"])
by_state["label"] = by_state.apply(
    lambda r: fmt(r["revenue"]) if r["customer_state"] in top5_states else "", axis=1
)
with col2:
    fig_state = px.bar(
        by_state,
        x="customer_state",
        y="revenue",
        title="Revenue by customer state (top 5 labeled)",
        labels={"revenue": f"Revenue ({symbol})", "customer_state": ""},
        text="label",
    )
    fig_state.update_traces(marker_color=GREEN, textposition="outside")
    st.plotly_chart(style_fig(fig_state), width="stretch")
