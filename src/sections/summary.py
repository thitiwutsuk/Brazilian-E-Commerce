import plotly.graph_objects as go
import streamlit as st

from src.currency import fmt_money_short
from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, reporting_periods, scorecard
from src.sections.recommendations import recommendations
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
    card = scorecard()
    recs = recommendations()
    monthly = monthly_kpis().set_index("month")
    crisis = crisis_months().set_index("month")
    last3 = monthly.tail(3)
    this_year = monthly[monthly.index.year == periods["as_of"].year]
    peak_month = monthly["orders"].idxmax()

    with st.container(border=True):
        st.markdown("#### Problem statement")
        st.markdown(
            "Olist grew very fast through 2017–2018. Fast growth raises a question management needs answered: "
            f"**is the growth healthy?** With Black Friday {periods['as_of'].year} three months away - our busiest "
            "period of the year - this review answers three questions:"
        )
        where = {1: "Sales & Growth, Customers & Markets", 2: "Customer Experience", 3: "Recommendations"}
        st.markdown("\n".join(f"{n}. **{q}** *(→ {where[n]})*" for n, q in QUESTIONS.items()))

    with st.container(border=True):
        st.markdown("#### Answers in short")
        st.markdown(
            f"1. **Yes, but growth has levelled off.** GMV {fmt_money_short(card.loc['gmv', 'current'])} "
            f"(**{card.loc['gmv', 'change']:+.0%}** YoY) on {card.loc['orders', 'current']:,.0f} orders, driven by the "
            f"jump around Black Friday {peak_month:%Y}; since then volume is flat at "
            f"{this_year['orders'].min() / 1000:.1f}–{this_year['orders'].max() / 1000:.1f}K orders a month, and a few "
            "categories and sellers carry most of the revenue.\n"
            f"2. **No - delivery did not keep up.** The late delivery rate rose from {card.loc['late', 'prior']:.1%} to "
            f"**{card.loc['late', 'current']:.1%}**, breaking down in the peak months "
            f"({', '.join(f'{m:%b %Y}' for m in crisis.index)}), and negative reviews rose to "
            f"**{card.loc['negative', 'current']:.1%}**. Only {card.loc['returning', 'current']:.1%} of orders come "
            "from returning customers.\n"
            f"3. **Secure delivery capacity for Black Friday {periods['as_of'].year} first**, then fix the worst-served "
            "states and start a second-purchase program.".replace("$", "\\$")
        )

    st.subheader("KPI scorecard")
    st.caption(f"{periods['label']} vs. the same months last year. Hover the ⓘ for the definition. "
               "Targets are proposed by Data Intelligence (see Appendix).")
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

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("#### ✅ What went well")
            st.markdown(
                f"- **Growth:** GMV {card.loc['gmv', 'change']:+.0%}, active customers "
                f"{card.loc['customers', 'change']:+.0%} YoY.\n"
                f"- **Order value held:** AOV {card.loc['aov', 'change']:+.1%} YoY despite the volume increase.\n"
                f"- **Fewer cancellations:** {card.loc['cancel', 'current']:.1%} of orders "
                f"(from {card.loc['cancel', 'prior']:.1%}).\n"
                f"- **Delivery recovered after March:** late rate {last3['late'].mean():.1%} on average over the last "
                "3 months.".replace("$", "\\$")
            )
    with col2:
        with st.container(border=True):
            st.markdown("#### ⚠️ What needs attention")
            st.markdown(
                f"- **Late deliveries doubled:** {card.loc['late', 'current']:.1%} vs. target "
                f"{KPI_BY_KEY['late'].target:.0%}.\n"
                f"- **Negative reviews up:** {card.loc['negative', 'current']:.1%} of reviews are 1–2 stars "
                f"(target ≤ {KPI_BY_KEY['negative'].target:.0%}).\n"
                f"- **Low loyalty:** {card.loc['returning', 'current']:.1%} of orders from returning customers.\n"
                "- **Concentration risk:** a small group of sellers and categories carries most of the revenue."
            )

    st.subheader(f"Q3 · {QUESTIONS[3]}")
    for i, r in enumerate(recs[:3], 1):
        st.markdown(f"{i}. **{r['title']}** ({r['priority']} priority, {r['owner']}) - {r['impact']}".replace("$", "\\$"))
    st.caption("Full evidence, actions and impact sizing in the *Recommendations* tab.")
