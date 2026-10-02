import plotly.graph_objects as go
import streamlit as st

from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, reporting_periods
from src.story import QUESTIONS, annotate_crises, crisis_months
from src.theme import ACCENT_RED, GRID_GREY, INK, style_fig, takeaway


def _growth_vs_reliability_fig():
    m = monthly_kpis()
    late_target = KPI_BY_KEY["late"].target
    fig = go.Figure()
    fig.add_bar(x=m["month"], y=m["orders"], name="Orders", marker_color=GRID_GREY, marker_line_width=0)
    fig.add_scatter(x=m["month"], y=m["late"] * 100, name="Late delivery rate (%)", yaxis="y2",
                    mode="lines+markers", line=dict(color=ACCENT_RED, width=3))
    fig.add_scatter(x=m["month"], y=[late_target * 100] * len(m), name=f"Late-rate target ({late_target:.0%})",
                    yaxis="y2", mode="lines", line=dict(color=INK, dash="dot", width=1))
    fig.update_layout(
        title="Orders kept growing - delivery reliability broke at the peaks",
        yaxis=dict(title="Orders", showgrid=False),
        yaxis2=dict(title="Late deliveries (%)", overlaying="y", side="right", rangemode="tozero", showgrid=True,
                    gridcolor=GRID_GREY),
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
        hovermode="x unified",
    )
    annotate_crises(fig, yref="y2")
    return style_fig(fig)


def render() -> None:
    periods = reporting_periods()
    monthly = monthly_kpis().set_index("month")
    crisis = crisis_months().set_index("month")
    last3 = monthly.tail(3)

    with st.container(border=True):
        st.markdown("#### Problem statement")
        st.markdown(
            "Olist grew very fast through 2017–2018. Fast growth raises a question management needs answered: "
            f"**is the growth healthy?** With Black Friday {periods['as_of'].year} three months away - our busiest "
            "period of the year - this review answers three questions:"
        )
        where = {1: "Sales & Growth, Customers & Markets", 2: "Customer Experience", 3: "Recommendations"}
        st.markdown("\n".join(f"{n}. **{q}** *(→ {where[n]})*" for n, q in QUESTIONS.items()))

    st.subheader("KPI scorecard")
    st.caption(f"{periods['label']} vs. the same months last year. Hover the ⓘ for the definition. "
               "Targets are proposed, not official (see Appendix).")
    st.markdown("**Growth**")
    render_cards(["gmv", "orders", "aov", "customers"])
    st.markdown("**Customer health**")
    render_cards(["late", "negative", "review", "returning"])

    st.subheader("The story in one chart")
    st.plotly_chart(_growth_vs_reliability_fig())
    normal = monthly.loc[monthly.index < crisis.index.min(), "late"].median()
    takeaway(
        f"In normal months about {normal:.0%} of orders arrive late. When demand peaked, the late rate jumped to "
        f"{', '.join(f'{r.late:.0%} ({m:%b %Y})' for m, r in crisis.iterrows())}. It has since recovered to "
        f"{last3['late'].mean():.1%} on average over the last 3 months. The system works at normal load but breaks at "
        "peak load - that is what to fix before November."
    )
