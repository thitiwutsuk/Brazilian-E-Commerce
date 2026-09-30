import streamlit as st

from src.currency import fmt_money, fmt_money_short
from src.data_loader import load_order_level
from src.metrics import (
    category_pareto,
    delivered_orders,
    late_vs_on_time,
    n_for_share,
    orders_per_customer,
    peak_day,
    yoy_growth,
)
from src.quality import analysis_window, grain_comparison
from src.theme import key_findings


def render() -> None:
    orders = load_order_level()
    start, end = analysis_window()
    st.markdown(
        f"An analysis of **{len(orders):,} orders** from Olist, a Brazilian marketplace "
        f"({orders['order_purchase_timestamp'].min():%b %Y} – {orders['order_purchase_timestamp'].max():%b %Y}). "
        "The tabs follow the analysis in order: **schema → data quality → cleaning & modeling → sales → "
        "delivery & satisfaction → customers**. Each ends with its key findings."
    )

    valid = orders[orders["order_status"] != "canceled"]
    freq = orders_per_customer()
    d = delivered_orders()
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Orders", f"{len(orders):,}")
    col2.metric("Customers", f"{len(freq):,}")
    col3.metric("Revenue", fmt_money_short(valid["payment_value"].sum()))
    col4.metric("Avg. order value", fmt_money(valid["payment_value"].mean()))
    col5.metric("Avg. review", f"{orders['review_score'].mean():.2f} / 5")
    col6.metric("Late deliveries", f"{d['is_late'].mean():.1%}")

    grains = grain_comparison()
    lvo = late_vs_on_time()
    late, on_time = lvo.loc["Late"], lvo.loc["On time / early"]
    yoy = yoy_growth()
    peak = peak_day()
    cats = category_pareto()

    key_findings(
        [
            f"**Data: a naive join inflates revenue by {grains.iloc[0]['vs. order fact']:.0%}.** Order-level payments "
            "repeat on every item row; the report uses two fact tables with an explicit grain instead. "
            "*(Schema, Cleaning & Modeling)*",
            f"**Delivery drives satisfaction:** late orders average {late['avg_review']:.2f} stars vs. "
            f"{on_time['avg_review']:.2f}, and are {late['negative_share'] / on_time['negative_share']:.1f}x as likely "
            "to get a 1–2 star review. *(Delivery & Satisfaction)*",
            f"**Customers rarely return:** {(freq == 1).mean():.0%} bought only once - retention is the biggest "
            "untapped lever. *(Customers & Geography)*",
            f"**Growth has plateaued after a Black Friday peak:** {peak['date']:%d %b %Y} was the busiest day "
            f"({int(peak['orders']):,} orders); {yoy['year']} is {yoy['orders']:+.0%} YoY but flat month to month. *(Sales)*",
            f"**Revenue is concentrated:** {n_for_share(cats)} of {len(cats)} categories make 80% of revenue. *(Sales)*",
        ],
    )
    st.caption(
        f"Revenue excludes canceled orders and is shown in USD at a fixed rate (see README). Trend charts use "
        f"{start:%b %Y} – {end:%b %Y}, the months with full data coverage (see *Data Quality*)."
    )
