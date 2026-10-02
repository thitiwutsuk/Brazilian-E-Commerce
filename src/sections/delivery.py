import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, scorecard
from src.story import QUESTIONS, annotate_crises, crisis_months, highlight_crises, question_label
from src.metrics import LOW_SCORE, delivered_orders, late_vs_on_time
from src.theme import ACCENT_RED, BRAND_COLOR, INK, key_findings, section_header, style_fig, takeaway

DELAY_BUCKETS = [
    (-999, 0, "On time or early"),
    (1, 3, "1–3 days late"),
    (4, 7, "4–7 days late"),
    (8, 999, "8+ days late"),
]


def _bucket(delay: pd.Series) -> pd.Series:
    labels = [b[2] for b in DELAY_BUCKETS]
    out = pd.Series(pd.NA, index=delay.index, dtype="object")
    for lo, hi, label in DELAY_BUCKETS:
        out[delay.between(lo, hi)] = label
    return pd.Categorical(out, categories=labels, ordered=True)


def _trend_fig():
    mk = monthly_kpis()
    fig = go.Figure()
    fig.add_scatter(x=mk["month"], y=mk["late"] * 100, name="Late deliveries (%)", mode="lines+markers",
                    line=dict(color=ACCENT_RED, width=3))
    fig.add_scatter(x=mk["month"], y=mk["negative"] * 100, name=f"1–{LOW_SCORE} star reviews (%)",
                    mode="lines+markers", line=dict(color=INK, width=2))
    fig.add_hline(y=KPI_BY_KEY["late"].target * 100, line_dash="dot", line_color=ACCENT_RED,
                  annotation_text=f"late-rate target {KPI_BY_KEY['late'].target:.0%}", annotation_position="top left")
    highlight_crises(fig)
    annotate_crises(fig, below=True)
    fig.update_layout(title="Late deliveries vs. negative reviews, by month", yaxis_title="%",
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"), hovermode="x unified")
    return style_fig(fig)


def _impact_fig(by_bucket: pd.DataFrame):
    is_late = by_bucket["bucket"].astype(str).str.contains("late")
    fig = px.bar(by_bucket, x="bucket", y="negative", title="The later the delivery, the worse the review",
                 labels={"bucket": "", "negative": f"% of orders rated 1–{LOW_SCORE} stars"},
                 text=by_bucket["negative"].map(lambda v: f"{v:.0f}%"), hover_data={"orders": ":,"})
    fig.update_traces(marker_color=[ACCENT_RED if x else BRAND_COLOR for x in is_late], textposition="outside")
    fig.update_yaxes(range=[0, by_bucket["negative"].max() * 1.2])
    return style_fig(fig)


def render() -> None:
    section_header(f"{question_label(2)} · {QUESTIONS[2]}")
    card = scorecard()
    lvo = late_vs_on_time()
    late, on_time = lvo.loc["Late"], lvo.loc["On time / early"]
    crisis = crisis_months()
    r = delivered_orders().dropna(subset=["review_score"])
    by_bucket = (
        r.assign(bucket=_bucket(r["delay_days"]))
        .groupby("bucket", observed=True)
        .agg(orders=("order_id", "size"), negative=("review_score", lambda s: (s <= LOW_SCORE).mean() * 100))
        .reset_index()
    )
    risk = late["negative_share"] / on_time["negative_share"]

    st.subheader("1. Experience at a Glance")
    render_cards(["late", "negative", "review", "delivery_days"])
    takeaway(f"Late deliveries more than doubled ({card.loc['late', 'prior']:.1%} → {card.loc['late', 'current']:.1%}) "
             "while delivery speed stayed the same.", label="Insight")

    st.subheader("2. Monthly Delivery Trend")
    st.plotly_chart(_trend_fig())
    takeaway("Late deliveries spike at demand peaks - and negative reviews rise with them.", label="Insight")

    st.subheader("3. Impact on Customer Reviews")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_impact_fig(by_bucket))
    with col2:
        with st.container(border=True):
            st.metric(f"1–{LOW_SCORE} star reviews: late vs. on time",
                      f"{late['negative_share']:.0%} vs. {on_time['negative_share']:.0%}")
        with st.container(border=True):
            st.metric("Likelihood of a bad review when late", f"{risk:.1f}x")

    key_findings(
        [
            f"**Not keeping up:** the late rate doubled to {card.loc['late', 'current']:.1%} "
            f"(target {KPI_BY_KEY['late'].target:.0%}).",
            f"**Peaks break delivery:** {', '.join(f'{m:%b %Y} ({v:.0%})' for m, v in zip(crisis['month'], crisis['late']))}.",
            f"**Late = unhappy:** a late order is {risk:.1f}x as likely to get a 1–{LOW_SCORE} star review.",
        ],
        so_what="Protect the promised delivery date, especially at peak demand.",
    )
