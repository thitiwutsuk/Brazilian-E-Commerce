import plotly.express as px
import streamlit as st

from src.data_loader import load_order_level, load_raw
from src.metrics import orders_per_customer
from src.kpis import render_cards
from src.story import question_label
from src.theme import BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway


def render() -> None:
    section_header(
        f"{question_label(1, 2)} · Who buys from us, do they come back, and where are they?",
        "Customers counted as people (customer_unique_id), all orders to date. Purchase frequency, share of "
        "orders and GMV by state.",
    )
    orders = load_order_level()
    freq = orders_per_customer()
    repeat = freq[freq > 1]

    render_cards(["customers", "returning"], per_row=2)

    col1, col2 = st.columns(2)
    with col1:
        buckets = freq.clip(upper=4).value_counts().sort_index()
        dist = buckets.rename(index={4: "4+"}).rename_axis("orders").reset_index(name="customers")
        dist["orders"] = dist["orders"].astype(str)
        dist["pct"] = dist["customers"] / dist["customers"].sum() * 100
        fig = px.bar(dist, x="orders", y="customers", title="Customers by number of orders",
                     labels={"orders": "Orders per customer", "customers": "Customers"},
                     text=dist["pct"].map(lambda v: f"{v:.1f}%"))
        fig.update_traces(marker_color=[BRAND_COLOR] + [NEUTRAL_GREY] * (len(dist) - 1), textposition="outside")
        fig.update_yaxes(range=[0, dist["customers"].max() * 1.15])
        st.plotly_chart(style_fig(fig))
    with col2:
        by_state = orders.groupby("customer_state").agg(orders=("order_id", "size"), revenue=("payment_value", "sum"))
        by_state = (by_state / by_state.sum() * 100).sort_values("orders", ascending=False).head(8).reset_index()
        long = by_state.melt(id_vars="customer_state", var_name="measure", value_name="pct")
        fig = px.bar(long, x="customer_state", y="pct", color="measure", barmode="group",
                     title="Share of orders and revenue - top 8 states",
                     labels={"customer_state": "", "pct": "Share (%)", "measure": ""},
                     color_discrete_map={"orders": BRAND_COLOR, "revenue": "#00893D"})
        fig.update_layout(legend=dict(orientation="h", y=1.08, x=1, xanchor="right"))
        st.plotly_chart(style_fig(fig))

    takeaway(
        f"{(freq == 1).mean():.0%} of customers have bought from us only once. Our growth depends on continually "
        f"acquiring new buyers, and 3 states ({', '.join(by_state['customer_state'].head(3))}) make up "
        f"{by_state['orders'].head(3).sum():.0f}% of orders - outside them we are still a small player."
    )

    sellers = load_raw("sellers")
    top = by_state.iloc[0]
    top3 = by_state.head(3)
    seller_sp = (sellers["seller_state"] == top["customer_state"]).mean()
    key_findings(
        [
            f"**Almost nobody comes back:** {(freq == 1).mean():.1%} of {len(freq):,} customers ordered once; only "
            f"{len(repeat):,} placed a second order. Growth has come from acquisition, not retention.",
            f"**Repeat customers are a small base with room to grow** - they average {repeat.mean():.1f} orders "
            f"each; every +1 point of repeat rate is about {len(freq) * 0.01:,.0f} extra customers buying again.",
            f"**Demand is concentrated in the south-east:** {top['customer_state']} alone is {top['orders']:.0f}% of "
            f"orders, and the top 3 states ({', '.join(top3['customer_state'])}) are {top3['orders'].sum():.0f}%.",
            f"**Supply is even more concentrated:** {seller_sp:.0%} of sellers are in {top['customer_state']}, which "
            "explains why distant states see longer and later deliveries (see *Customer Experience*).",
        ],
        so_what="Getting more customers to buy a second time is the cheapest growth lever we are not using; "
        "better delivery outside the south-east would support both growth and reviews there.",
    )
