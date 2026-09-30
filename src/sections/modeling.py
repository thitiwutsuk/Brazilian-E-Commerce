import plotly.express as px
import streamlit as st

from src.currency import fmt_money_short, get_currency
from src.data_loader import load_order_level
from src.quality import cleansing_log, grain_comparison
from src.theme import ACCENT_RED, BRAND_COLOR, key_findings, style_fig

ORDER_FACT_DICTIONARY = [
    ("order_id", "Primary key - one row per order", "orders"),
    ("customer_unique_id", "The actual customer (stable across orders)", "customers"),
    ("order_status", "delivered / shipped / canceled / unavailable / ...", "orders"),
    ("order_purchase_timestamp", "When the order was placed; `month` is its calendar month", "orders"),
    ("n_items, n_sellers", "Items and distinct sellers in the order (0 if no items)", "order_items (aggregated)"),
    ("item_price, freight_value", "Sum of item prices / freight in the order, BRL", "order_items (aggregated)"),
    ("payment_value", "Total paid for the order across all payments, BRL - the revenue measure", "order_payments (aggregated)"),
    ("payment_type", "Method of the largest payment in the order", "order_payments"),
    ("review_score", "1-5, latest review for the order", "order_reviews (deduplicated)"),
    ("delivery_days", "Purchase → delivered to customer, days", "derived"),
    ("delay_days", "Delivered minus estimated date, days (negative = early)", "derived"),
    ("is_late", "delay_days > 0", "derived"),
]


def render() -> None:
    grains = grain_comparison()
    naive, order_fact, item_fact = (grains.iloc[i] for i in range(3))
    symbol, rate = get_currency()

    with st.container(border=True):
        st.markdown(
            f"**The key catch: a standard join would have overstated revenue by {naive['vs. order fact']:.0%}.** "
            "One order can contain several items, but the payment is recorded once per order. Joining payments onto "
            f"items repeats the payment on every item row - {fmt_money_short(naive['Revenue (BRL)'])} instead of "
            f"{fmt_money_short(order_fact['Revenue (BRL)'])}.".replace("$", "\\$")
        )

    fig = px.bar(
        grains.assign(Method=["Standard join (wrong)", "Order level (used for totals)", "Item level (used for categories)"],
                      Revenue=grains["Revenue (BRL)"] / rate),
        x="Revenue", y="Method", orientation="h", title="Total revenue by calculation method",
        labels={"Revenue": f"Revenue ({symbol})", "Method": ""},
        text=grains["Revenue (BRL)"].map(fmt_money_short),
    )
    fig.update_traces(marker_color=[ACCENT_RED, BRAND_COLOR, BRAND_COLOR], textposition="inside")
    fig.update_layout(yaxis={"autorange": "reversed"}, height=300)
    st.plotly_chart(style_fig(fig))

    st.subheader("What was done to the raw data")
    log = cleansing_log()
    st.dataframe(
        log[["Table", "Step", "Rows before", "Rows after"]],
        width="stretch",
        hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="localized") for c in ["Rows before", "Rows after"]},
    )

    with st.expander("Data dictionary - order-level table"):
        orders = load_order_level()
        st.caption(f"{orders.shape[0]:,} rows × {orders.shape[1]} columns; key columns shown.")
        st.dataframe(
            [dict(Column=c, Definition=d, Source=s) for c, d, s in ORDER_FACT_DICTIONARY],
            width="stretch",
            hide_index=True,
        )

    log = log.set_index("Step")
    key_findings(
        [
            f"**Revenue in this report is correct:** totals use one row per order ({order_fact['Rows']:,} orders), "
            "category and seller splits use one row per item, and the build stops if an order is ever duplicated.",
            f"**Cleaning removed duplicates, not sales:** {-log.iloc[0]['Change']:,} duplicate reviews were dropped; "
            "no order is removed from revenue totals.",
        ],
    )
