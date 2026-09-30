import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards
from src.metrics import LOW_SCORE, delivered_orders, late_vs_on_time
from src.theme import ACCENT_RED, BRAND_COLOR, INK, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

MIN_STATE_ORDERS = 300  # ignore states too small for a stable late rate

DELAY_BUCKETS = [
    (-999, -15, "15+ days early"),
    (-14, -8, "8–14 early"),
    (-7, -1, "1–7 early"),
    (0, 0, "On the day"),
    (1, 3, "1–3 late"),
    (4, 7, "4–7 late"),
    (8, 999, "8+ days late"),
]


def _bucket(delay: pd.Series) -> pd.Series:
    labels = [b[2] for b in DELAY_BUCKETS]
    out = pd.Series(pd.NA, index=delay.index, dtype="object")
    for lo, hi, label in DELAY_BUCKETS:
        out[delay.between(lo, hi)] = label
    return pd.Categorical(out, categories=labels, ordered=True)


def render() -> None:
    section_header(
        "Are customers getting what we promised, and what happens when we miss?",
        "Delivered orders only. Late = delivered after the date promised at checkout. Reviews compared across "
        f"delay buckets; a 1–{LOW_SCORE} star review counts as negative.",
    )
    d = delivered_orders()
    lvo = late_vs_on_time()
    late, on_time = lvo.loc["Late"], lvo.loc["On time / early"]

    render_cards(["late", "negative", "review", "delivery_days"])

    st.subheader("Monthly trend")
    mk = monthly_kpis()
    fig = go.Figure()
    fig.add_scatter(x=mk["month"], y=mk["late"] * 100, name="Late deliveries (%)", mode="lines+markers",
                    line=dict(color=ACCENT_RED, width=3))
    fig.add_scatter(x=mk["month"], y=mk["negative"] * 100, name=f"1–{LOW_SCORE} star reviews (%)",
                    mode="lines+markers", line=dict(color=INK, width=2))
    fig.add_hline(y=KPI_BY_KEY["late"].target * 100, line_dash="dot", line_color=ACCENT_RED,
                  annotation_text=f"late-rate target {KPI_BY_KEY['late'].target:.0%}", annotation_position="top left")
    fig.update_layout(title="Late deliveries and negative reviews move together", yaxis_title="%",
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"), hovermode="x unified")
    st.plotly_chart(style_fig(fig))
    worst_m = mk.loc[mk["late"].idxmax()]
    corr = mk["late"].corr(mk["negative"])
    takeaway(
        f"In the worst month ({worst_m['month']:%b %Y}) {worst_m['late']:.0%} of orders arrived late and "
        f"{worst_m['negative']:.0%} of reviews were negative. Month to month, the two lines move almost in step "
        f"(correlation {corr:.2f}): when delivery slips, reviews follow."
    )
    st.caption("Note: the latest months can look better than they will end up - orders still in transit at the "
               "data cut-off are not counted as delivered yet, and the late ones are usually among them.")

    st.subheader("Delay vs. satisfaction")
    r = d.dropna(subset=["review_score"]).assign(bucket=lambda x: _bucket(x["delay_days"]))
    by_bucket = r.groupby("bucket", observed=True).agg(
        orders=("order_id", "size"),
        avg_review=("review_score", "mean"),
        negative=("review_score", lambda s: (s <= LOW_SCORE).mean() * 100),
    ).reset_index()
    is_late_bucket = by_bucket["bucket"].astype(str).str.contains("late")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(by_bucket, x="bucket", y="avg_review", title="Avg. review score by delivery delay",
                     labels={"bucket": "", "avg_review": "Avg. review score"},
                     text=by_bucket["avg_review"].map(lambda v: f"{v:.2f}"), hover_data={"orders": ":,"})
        fig.update_traces(marker_color=[ACCENT_RED if x else BRAND_COLOR for x in is_late_bucket], textposition="outside")
        fig.update_yaxes(range=[0, 5.4])
        st.plotly_chart(style_fig(fig))
    with col2:
        fig = px.bar(by_bucket, x="bucket", y="negative", title=f"Share of 1–{LOW_SCORE} star reviews by delivery delay",
                     labels={"bucket": "", "negative": "Negative reviews (%)"},
                     text=by_bucket["negative"].map(lambda v: f"{v:.0f}%"), hover_data={"orders": ":,"})
        fig.update_traces(marker_color=[ACCENT_RED if x else BRAND_COLOR for x in is_late_bucket], textposition="outside")
        fig.update_yaxes(range=[0, by_bucket["negative"].max() * 1.2])
        st.plotly_chart(style_fig(fig))

    neg = by_bucket.set_index(by_bucket["bucket"].astype(str))["negative"]
    takeaway(
        f"Arriving early barely changes the score ({neg.iloc[0]:.0f}–{neg.loc['On the day']:.0f}% negative), but "
        f"every day late costs us: {neg.loc['1–3 late']:.0f}% negative at 1–3 days late and "
        f"{neg.iloc[-1]:.0f}% beyond a week. Keeping the promised date matters more than delivering faster."
    )

    st.dataframe(
        lvo.reset_index().rename(columns={"is_late": "Delivery", "orders": "Orders", "avg_review": "Avg. review",
                                          "negative_share": f"1–{LOW_SCORE} star share"}),
        width="stretch",
        hide_index=True,
        column_config={
            "Orders": st.column_config.NumberColumn(format="localized"),
            "Avg. review": st.column_config.NumberColumn(format="%.2f"),
            f"1–{LOW_SCORE} star share": st.column_config.NumberColumn(format="percent"),
        },
    )

    st.subheader("Where lateness happens")
    col1, col2 = st.columns(2)
    national = d["is_late"].mean() * 100
    with col1:
        by_state = d.groupby("customer_state").agg(orders=("order_id", "size"), late=("is_late", "mean")).reset_index()
        by_state = by_state[by_state["orders"] >= MIN_STATE_ORDERS].sort_values("late", ascending=False).head(10)
        by_state["pct"] = by_state["late"] * 100
        fig = px.bar(by_state.sort_values("pct"), x="pct", y="customer_state", orientation="h",
                     title=f"Late rate - worst 10 states (dotted line = national {national:.1f}%)",
                     labels={"pct": "Late deliveries (%)", "customer_state": ""},
                     text=by_state.sort_values("pct")["pct"].map(lambda v: f"{v:.0f}%"), hover_data={"orders": ":,"})
        fig.update_traces(marker_color=BRAND_COLOR, textposition="outside")
        fig.add_vline(x=national, line_color=NEUTRAL_GREY, line_dash="dot")
        fig.update_layout(xaxis_range=[0, by_state["pct"].max() * 1.2])
        st.plotly_chart(style_fig(fig))
        st.caption(f"States with ≥{MIN_STATE_ORDERS} delivered orders, all orders to date.")
    with col2:
        p99 = d["delivery_days"].quantile(0.99)
        fig = px.histogram(d, x="delivery_days", nbins=60, title="Delivery time distribution",
                           labels={"delivery_days": "Delivery time (days)"})
        fig.update_traces(marker_color=BRAND_COLOR)
        fig.add_vline(x=d["delivery_days"].median(), line_color=NEUTRAL_GREY,
                      annotation_text=f"median {d['delivery_days'].median():.0f}d", annotation_position="top right")
        # The ~1% tail runs past 200 days and would squash the distribution.
        fig.update_xaxes(range=[0, p99])
        st.plotly_chart(style_fig(fig))
        st.caption(f"X-axis capped at the 99th percentile ({p99:.0f} days).")

    worst = by_state.iloc[0]
    early = by_bucket.iloc[0]
    worst_late = by_bucket.iloc[-1]
    key_findings(
        [
            f"**Late delivery is uncommon but costly:** across all deliveries to date, {d['is_late'].mean():.1%} "
            f"arrived after the promised date. Their average review is **{late['avg_review']:.2f}** vs. **{on_time['avg_review']:.2f}** "
            "for on-time orders.",
            f"**A late order is {late['negative_share'] / on_time['negative_share']:.1f}x as likely to get a 1–{LOW_SCORE} "
            f"star review** ({late['negative_share']:.0%} vs. {on_time['negative_share']:.0%}).",
            f"**The effect grows with the delay:** negative reviews rise from {early['negative']:.0f}% for orders "
            f"{early['bucket']} to {worst_late['negative']:.0f}% for {worst_late['bucket']} "
            f"(avg. score {early['avg_review']:.2f} → {worst_late['avg_review']:.2f}).",
            f"**Estimates are padded:** the typical order arrives {-d.loc[~d['is_late'], 'delay_days'].median():.0f} days "
            "early, so 'on time' mostly means 'well ahead of a conservative promise'.",
            f"**Lateness is regional:** {worst['customer_state']} ({worst['pct']:.0f}%) and "
            f"{by_state.iloc[1]['customer_state']} ({by_state.iloc[1]['pct']:.0f}%) run at "
            f"{worst['pct'] / national:.1f}x the national {national:.1f}% late rate - mostly north-eastern states "
            "far from the south-east seller base.",
        ],
        so_what="Keeping the delivery promise - especially at peak and in the north-east - is the most direct "
        "lever on review scores. (These are associations in historical data, not proven causes; product and "
        "seller also play a part.)",
    )
