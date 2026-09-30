import plotly.graph_objects as go
import streamlit as st

from src.currency import fmt_money_short
from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, reporting_periods, scorecard
from src.sections.recommendations import recommendations
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
    return style_fig(fig)


def render() -> None:
    periods = reporting_periods()
    card = scorecard()
    recs = recommendations()
    monthly = monthly_kpis().set_index("month")
    crisis = monthly[monthly["late"] > 2 * KPI_BY_KEY["late"].target]
    last3 = monthly.tail(3)

    with st.container(border=True):
        st.markdown("#### Bottom line")
        st.markdown(
            f"We more than doubled the business - GMV **{fmt_money_short(card.loc['gmv', 'current'])}** "
            f"(**{card.loc['gmv', 'change']:+.0%}** YoY) on **{card.loc['orders', 'current']:,.0f}** orders - "
            f"but **delivery did not keep up**. The late delivery rate rose from {card.loc['late', 'prior']:.1%} to "
            f"**{card.loc['late', 'current']:.1%}**, pushing negative reviews to **{card.loc['negative', 'current']:.1%}**. "
            f"The damage came from peak months ({', '.join(f'{m:%b %Y}' for m in crisis.index)}) and has since "
            f"recovered, which makes **Black Friday {periods['as_of'].year} the main risk** for the rest of the year. "
            f"Growth is also almost entirely new customers: only **{card.loc['returning', 'current']:.1%}** of orders "
            "come from returning buyers.".replace("$", "\\$")
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
    takeaway(
        f"Late deliveries stayed near {monthly.loc[:crisis.index.min()].iloc[:-1]['late'].median():.0%} while volume "
        f"grew steadily, then spiked to {crisis['late'].max():.0%} when demand peaked. Since then the rate is back "
        f"to {last3['late'].min():.0%}–{last3['late'].max():.0%}. The system works at normal load and breaks at "
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

    st.subheader("Recommended actions")
    for i, r in enumerate(recs[:3], 1):
        st.markdown(f"{i}. **{r['title']}** ({r['priority']} priority, {r['owner']}) - {r['impact']}".replace("$", "\\$"))
    st.caption("Full evidence, actions and impact sizing in the *Recommendations* tab.")
