import pandas as pd
import plotly.express as px
import streamlit as st

from src.currency import get_currency
from src.kpis import render_cards, reporting_periods, scorecard
from src.metrics import category_pareto, monthly_sales, n_for_share, peak_day, seller_pareto, yoy_growth
from src.story import QUESTIONS, question_label
from src.theme import ACCENT_RED, BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

TOP_CATEGORIES = 10


def _phases(m: pd.DataFrame, periods: dict) -> dict:
    """Split the timeline into ramp-up, Black Friday step, and plateau, and size each phase's share of the
    YoY order growth (Jan-Aug this year vs. the same months last year)."""
    peak = m.loc[m["orders"].idxmax(), "month"]
    plateau_start, plateau_end = periods["current"]
    prior_start, prior_end = periods["prior"]
    avg = lambda a, b: m.loc[m["month"].between(a, b), "orders"].mean()
    prior = avg(prior_start, prior_end)
    pre_peak = avg(peak - pd.DateOffset(months=2), peak - pd.DateOffset(months=1))
    current = avg(plateau_start, plateau_end)
    gap = current - prior
    return dict(
        peak=peak, plateau=(plateau_start, plateau_end),
        ramp=(m["month"].min(), peak - pd.DateOffset(months=1)), step=(peak, plateau_start - pd.DateOffset(months=1)),
        ramp_share=(pre_peak - prior) / gap, step_share=(current - pre_peak) / gap,
    )


def _timeline_fig(m: pd.DataFrame, ph: dict, peak_d: pd.Series):
    fig = px.line(m, x="month", y="orders", markers=True, title="Monthly orders",
                  labels={"orders": "Orders", "month": ""})
    fig.update_traces(line_color=BRAND_COLOR, marker_color=BRAND_COLOR)
    half_month = pd.Timedelta(days=15)
    # The Black Friday band is narrow, so the plateau label sits on the far side of its band.
    for (a, b), label, color, pos in [(ph["ramp"], "Ramp-up", NEUTRAL_GREY, "top left"),
                                      (ph["step"], "Black Friday", ACCENT_RED, "top left"),
                                      (ph["plateau"], "Plateau", BRAND_COLOR, "top right")]:
        fig.add_vrect(x0=a - half_month, x1=b + half_month, fillcolor=color, opacity=0.08, line_width=0,
                      layer="below", annotation_text=f"<b>{label}</b>", annotation_position=pos)
    fig.add_annotation(x=ph["peak"], y=m["orders"].max(), showarrow=True, arrowhead=0, ax=60, ay=-30,
                       text=f"{int(peak_d['orders']):,} orders in one day")
    fig.update_layout(yaxis_range=[0, m["orders"].max() * 1.3])
    return style_fig(fig)


def _volume_share(card: pd.DataFrame) -> float:
    """Share of the GMV change explained by more orders (at last year's order value)."""
    volume = (card.loc["orders", "current"] - card.loc["orders", "prior"]) * card.loc["aov", "prior"]
    return volume / (card.loc["gmv", "current"] - card.loc["gmv", "prior"])


def _category_fig(cats: pd.DataFrame):
    top = cats.head(TOP_CATEGORIES).iloc[::-1]
    fig = px.bar(top, x=top["share"] * 100, y="product_category_name_english", orientation="h",
                 title=f"Share of revenue - top {TOP_CATEGORIES} categories",
                 labels={"x": "Share of revenue (%)", "product_category_name_english": ""},
                 text=(top["share"] * 100).map(lambda v: f"{v:.1f}%"))
    fig.update_traces(marker_color=BRAND_COLOR, textposition="outside")
    fig.update_layout(xaxis_range=[0, top["share"].max() * 100 * 1.25])
    return style_fig(fig)


def render() -> None:
    section_header(f"{question_label(1)} · {QUESTIONS[1]}")
    symbol, rate = get_currency()
    periods = reporting_periods()
    card = scorecard()
    m = monthly_sales()
    yoy = yoy_growth()
    peak_d = peak_day()
    cats = category_pareto()
    sellers = seller_pareto()
    n80 = n_for_share(cats)

    volume_share = _volume_share(card)
    top_sellers_share = sellers.head(len(sellers) // 10)["share"].sum()

    st.subheader("1. Growth at a Glance")
    render_cards(["gmv", "orders", "aov", "customers"])
    takeaway(f"{volume_share:.0%} of GMV growth came from more orders - order value is flat.", label="Insight")

    st.subheader("2. How We Grew")
    ph = _phases(m, periods)
    this_year = m[m["month"].between(*ph["plateau"])]
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_timeline_fig(m, ph, peak_d))
    with col2:
        st.caption(f"Where the {card.loc['orders', 'change']:+.0%} YoY order growth came from")
        with st.container(border=True):
            st.metric(f"{ph['ramp'][0]:%Y} ramp-up", f"{ph['ramp_share']:.0%}")
        with st.container(border=True):
            st.metric(f"Black Friday {ph['peak']:%Y} step", f"{ph['step_share']:.0%}")
    takeaway(f"All of the growth happened in {ph['peak']:%Y}; {yoy['year']} has been flat.", label="Insight")
    with st.expander("Monthly data"):
        st.dataframe(
            m.assign(revenue=m["revenue"] / rate),
            width="stretch",
            hide_index=True,
            column_config={
                "month": st.column_config.DateColumn("Month", format="MMM YYYY"),
                "orders": st.column_config.NumberColumn("Orders", format="localized"),
                "revenue": st.column_config.NumberColumn(f"GMV ({symbol})", format="dollar"),
                "orders_mom": st.column_config.NumberColumn("Orders MoM", format="percent"),
                "revenue_mom": st.column_config.NumberColumn("GMV MoM", format="percent"),
            },
        )

    st.subheader("3. Revenue Concentration")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_category_fig(cats))
    with col2:
        with st.container(border=True):
            st.metric("Categories making 80% of revenue", f"{n80} of {len(cats)}")
        with st.container(border=True):
            st.metric("Revenue from top 10% of sellers", f"{top_sellers_share:.0%}")

    key_findings(
        [
            f"**Growing, but no longer accelerating:** GMV {card.loc['gmv', 'change']:+.0%} YoY, yet flat at "
            f"{this_year['orders'].min() / 1000:.1f}–{this_year['orders'].max() / 1000:.1f}K orders a month in {yoy['year']}.",
            f"**Volume-driven:** {volume_share:.0%} of the growth is more orders; order value is flat "
            f"({card.loc['aov', 'change']:+.0%}).",
            f"**Concentrated:** {n80} categories and the top 10% of sellers carry most of the revenue.",
        ],
        so_what=f"Protect the top categories and sellers, and plan volume around Black Friday {periods['as_of'].year}.",
    )
