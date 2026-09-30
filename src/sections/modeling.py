import plotly.express as px
import streamlit as st

from src.currency import fmt_money_short, get_currency
from src.data_loader import load_order_level
from src.quality import cleansing_log, grain_comparison
from src.theme import ACCENT_RED, BRAND_COLOR, key_findings, section_header, style_fig

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
    section_header(
        "How should the tables be combined so every number adds up?",
        "Logged row counts before/after each preparation step, then compared revenue computed at three "
        "different grains against the reconciled payment total.",
    )

    st.subheader("Cleansing log")
    log = cleansing_log()
    st.dataframe(
        log,
        width="stretch",
        hide_index=True,
        column_config={c: st.column_config.NumberColumn(format="localized") for c in ["Rows before", "Rows after", "Change"]},
    )

    st.subheader("Grain check: which join gives the right revenue?")
    grains = grain_comparison()
    symbol, rate = get_currency()
    grains["Revenue"] = grains["Revenue (BRL)"] / rate
    col1, col2 = st.columns([3, 2])
    with col1:
        st.dataframe(
            grains.drop(columns=["Revenue (BRL)"]),
            width="stretch",
            hide_index=True,
            column_config={
                "Rows": st.column_config.NumberColumn(format="localized"),
                "Revenue": st.column_config.NumberColumn(f"Revenue ({symbol})", format="dollar"),
                "vs. order fact": st.column_config.NumberColumn(format="percent"),
            },
        )
    with col2:
        fig = px.bar(grains.assign(Method=["Naive join", "Order fact", "Item fact"]), x="Revenue", y="Method",
                     orientation="h", title="Total revenue by method",
                     labels={"Revenue": f"Revenue ({symbol})", "Method": ""},
                     text=grains["Revenue (BRL)"].map(fmt_money_short))
        fig.update_traces(marker_color=[ACCENT_RED, BRAND_COLOR, BRAND_COLOR], textposition="inside")
        fig.update_layout(yaxis={"autorange": "reversed"})
        st.plotly_chart(style_fig(fig))

    st.subheader("Analysis-ready model")
    st.markdown(
        "- **Order fact** (`load_order_level`) - grain: 1 row per order. Used for revenue totals, AOV, delivery, "
        "reviews and customers.\n"
        "- **Item fact** (`load_item_level`) - grain: 1 row per order item, revenue = price + freight. Used for "
        "category and seller breakdowns."
    )
    orders = load_order_level()
    st.caption(f"Order fact data dictionary ({orders.shape[0]:,} rows × {orders.shape[1]} columns, key columns shown):")
    st.dataframe(
        [dict(Column=c, Definition=d, Source=s) for c, d, s in ORDER_FACT_DICTIONARY],
        width="stretch",
        hide_index=True,
    )

    naive, order_fact, item_fact = (grains.iloc[i] for i in range(3))
    log = log.set_index("Step")
    key_findings(
        [
            f"**The naive join overstates revenue by {naive['vs. order fact']:.1%}** ({fmt_money_short(naive['Revenue (BRL)'])} vs. "
            f"{fmt_money_short(order_fact['Revenue (BRL)'])}). `payment_value` is per order, but joining items first repeats it on "
            f"every item row ({naive['Rows']:,} rows for {order_fact['Rows']:,} orders). Every revenue chart built on it was inflated.",
            f"**Fix: two fact tables with an explicit grain.** Payments and items are aggregated to the order *before* "
            f"joining; the order fact is asserted to keep exactly {order_fact['Rows']:,} unique orders.",
            f"**Item-level revenue (price + freight) lands {abs(item_fact['vs. order fact']):.1%} below payments** - the same gap "
            "seen in reconciliation (installment interest, plus paid orders that never had items). It is the correct "
            "base for category and seller splits, whose parts then sum to a known total.",
            f"**Preparation removes little real data:** dedup drops {-log.iloc[0]['Change']:,} duplicate reviews, "
            f"and only {-log.loc[log.index.str.startswith('Keep delivered'), 'Change'].iloc[0]:,} undelivered orders "
            "are left out of delivery analysis - nothing is dropped from revenue totals.",
        ],
        so_what="All revenue in this report comes from the order fact or the item fact - never the naive join.",
    )
