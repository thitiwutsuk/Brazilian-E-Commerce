import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import load_raw
from src.kpis import period_slice, render_cards, reporting_periods, scorecard
from src.metrics import orders_per_customer
from src.story import question_label
from src.theme import BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

TOP_STATES = 8


def _loyalty_fig(freq: pd.Series):
    dist = freq.clip(upper=4).value_counts().sort_index().rename(index={4: "4+"})
    dist = dist.rename_axis("orders").reset_index(name="customers")
    dist["orders"] = dist["orders"].astype(str).map(lambda n: f"{n} order" + ("" if n == "1" else "s"))
    dist["pct"] = dist["customers"] / dist["customers"].sum() * 100
    fig = px.bar(dist, x="orders", y="pct", title="Customers by number of orders placed",
                 labels={"orders": "", "pct": "% of customers"}, text=dist["pct"].map(lambda v: f"{v:.1f}%"))
    fig.update_traces(marker_color=[BRAND_COLOR] + [NEUTRAL_GREY] * (len(dist) - 1), textposition="outside")
    fig.update_yaxes(range=[0, 110])
    return style_fig(fig)


def _state_fig(share: pd.Series, label: str):
    top = share.head(TOP_STATES).iloc[::-1] * 100
    fig = px.bar(x=top.values, y=top.index, orientation="h", title=f"Share of orders by state - top {TOP_STATES}, {label}",
                 labels={"x": "Share of orders (%)", "y": ""}, text=[f"{v:.0f}%" for v in top.values])
    fig.update_traces(marker_color=[NEUTRAL_GREY] * (len(top) - 3) + [BRAND_COLOR] * 3, textposition="outside")
    fig.update_layout(xaxis_range=[0, top.max() * 1.2])
    return style_fig(fig)


def render() -> None:
    section_header(f"{question_label(1, 2)} · Who are our customers, and where are they?")
    periods = reporting_periods()
    card = scorecard()
    freq = orders_per_customer()
    cur = period_slice("current")
    share = cur["customer_state"].value_counts(normalize=True)
    top3 = share.head(3)
    sellers = load_raw("sellers")
    seller_share = (sellers["seller_state"] == share.index[0]).mean()

    st.subheader("1. Customers at a Glance")
    render_cards(["customers", "returning"], per_row=2)
    takeaway(f"The customer base grew {card.loc['customers', 'change']:+.0%}, but almost all of it is first-time buyers.",
             label="Insight")

    st.subheader("2. Customer Loyalty")
    st.plotly_chart(_loyalty_fig(freq))
    takeaway(f"{(freq == 1).mean():.0%} of customers have ordered only once.", label="Insight")

    st.subheader("3. Market Concentration")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_state_fig(share, periods["label"]))
    with col2:
        with st.container(border=True):
            st.metric(f"Orders from {', '.join(top3.index)}", f"{top3.sum():.0%}")
        with st.container(border=True):
            st.metric(f"Sellers based in {share.index[0]}", f"{seller_share:.0%}")

    key_findings(
        [
            f"**Acquisition-led growth:** {(freq == 1).mean():.0%} of customers bought once; only "
            f"{card.loc['returning', 'current']:.1%} of orders come from returning customers.",
            f"**Demand is concentrated:** {', '.join(top3.index)} make up {top3.sum():.0%} of orders.",
            f"**Supply is concentrated too:** {seller_share:.0%} of sellers are in {share.index[0]}, far from many customers.",
        ],
        so_what="Win second purchases, and improve reach and delivery outside the south-east.",
    )
