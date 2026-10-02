import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.currency import fmt_money_short, get_currency
from src.kpis import render_cards, reporting_periods, scorecard
from src.metrics import category_pareto, monthly_sales, n_for_share, peak_day, seller_pareto, yoy_growth
from src.story import QUESTIONS, question_label
from src.theme import ACCENT_RED, BRAND_COLOR, INK, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

TOP_CATEGORIES = 10


def _trend_fig(m: pd.DataFrame, yoy: dict, peak_d: pd.Series):
    df = m.assign(year=m["month"].dt.year.astype(str), month_name=m["month"].dt.strftime("%b"))
    this_year = m[m["month"].dt.year == yoy["year"]]
    peak_m = m.loc[m["orders"].idxmax()]
    fig = px.line(df, x="month_name", y="orders", color="year", markers=True, title="Monthly orders, year over year",
                  labels={"orders": "Orders", "month_name": "", "year": ""},
                  color_discrete_map={str(yoy["year"] - 1): NEUTRAL_GREY, str(yoy["year"]): BRAND_COLOR})
    fig.update_xaxes(categoryorder="array", categoryarray=pd.date_range("2000-01-01", periods=12, freq="MS").strftime("%b"))
    fig.add_hrect(y0=this_year["orders"].min(), y1=this_year["orders"].max(), fillcolor=BRAND_COLOR, opacity=0.08,
                  line_width=0, annotation_text=f"{yoy['year']}: {this_year['orders'].min() / 1000:.1f}–"
                  f"{this_year['orders'].max() / 1000:.1f}K / month", annotation_position="bottom left")
    fig.add_annotation(x=f"{peak_m['month']:%b}", y=peak_m["orders"], showarrow=True, arrowhead=0, ax=-60, ay=-40,
                       text=f"<b>Black Friday {peak_m['month']:%Y}</b><br>{int(peak_d['orders']):,} orders in one day "
                            f"({peak_d['orders'] / peak_d['median']:.0f}x normal)")
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
                      yaxis_range=[0, df["orders"].max() * 1.25])
    return style_fig(fig), this_year


def _drivers_fig(card: pd.DataFrame, periods: dict):
    """GMV bridge: last year -> + more orders -> + higher order value -> this year."""
    symbol, rate = get_currency()
    prior_gmv, cur_gmv = card.loc["gmv", "prior"], card.loc["gmv", "current"]
    volume = (card.loc["orders", "current"] - card.loc["orders", "prior"]) * card.loc["aov", "prior"]
    value = cur_gmv - prior_gmv - volume
    steps = [prior_gmv, volume, value, cur_gmv]
    fig = go.Figure(go.Waterfall(
        x=[periods["prior_label"], "More orders", "Higher order value", periods["label"]],
        y=[v / rate for v in steps],
        measure=["absolute", "relative", "relative", "total"],
        text=[fmt_money_short(prior_gmv), f"+{fmt_money_short(volume)}", f"{'+' if value >= 0 else ''}{fmt_money_short(value)}",
              fmt_money_short(cur_gmv)],
        textposition="outside",
        connector=dict(line=dict(color=NEUTRAL_GREY, dash="dot")),
        increasing=dict(marker=dict(color=BRAND_COLOR)),
        decreasing=dict(marker=dict(color=ACCENT_RED)),
        totals=dict(marker=dict(color=INK)),
    ))
    fig.update_layout(title="GMV bridge: what drove the growth", yaxis_title=f"GMV ({symbol})",
                      yaxis_range=[0, cur_gmv / rate * 1.2], showlegend=False)
    return style_fig(fig), volume / (cur_gmv - prior_gmv)


def _category_fig(cats: pd.DataFrame):
    top = cats.head(TOP_CATEGORIES).iloc[::-1]
    fig = px.bar(top, x=top["share"] * 100, y="product_category_name_english", orientation="h",
                 title=f"Share of revenue - top {TOP_CATEGORIES} categories",
                 labels={"x": "Share of revenue (%)", "product_category_name_english": ""},
                 text=(top["share"] * 100).map(lambda v: f"{v:.1f}%"))
    fig.update_traces(marker_color=BRAND_COLOR, textposition="outside")
    fig.update_layout(xaxis_range=[0, top["share"].max() * 100 * 1.25])
    return style_fig(fig)


def _seller_fig(sellers: pd.DataFrame):
    deciles = sellers.assign(decile=(sellers["rank"] - 1) * 10 // len(sellers) + 1)
    by_decile = deciles.groupby("decile", as_index=False)["share"].sum()
    by_decile["pct"] = by_decile["share"] * 100
    fig = px.bar(by_decile, x="decile", y="pct", title="Share of revenue by seller group",
                 labels={"decile": "Seller group (1 = top 10% of sellers)", "pct": "Share of revenue (%)"},
                 text=by_decile["pct"].map(lambda v: f"{v:.0f}%"))
    fig.update_traces(marker_color=[BRAND_COLOR] + [NEUTRAL_GREY] * 9, textposition="outside")
    fig.update_xaxes(dtick=1)
    fig.update_layout(yaxis_range=[0, by_decile["pct"].max() * 1.15])
    return style_fig(fig), by_decile


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

    st.subheader("1. Growth at a Glance")
    render_cards(["gmv", "orders", "aov", "customers"])

    st.subheader("2. Monthly Order Trend")
    fig, this_year = _trend_fig(m, yoy, peak_d)
    st.plotly_chart(fig)
    takeaway(f"A one-time step up at Black Friday {yoy['year'] - 1}, then flat through {yoy['year']}.", label="Insight")
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

    st.subheader("3. Growth Drivers")
    fig, volume_share = _drivers_fig(card, periods)
    st.plotly_chart(fig)
    takeaway(f"{volume_share:.0%} of GMV growth came from more orders, not bigger baskets.", label="Insight")

    st.subheader("4. Revenue by Category")
    st.plotly_chart(_category_fig(cats))
    takeaway(f"{n80} of {len(cats)} categories generate 80% of revenue.", label="Insight")

    st.subheader("5. Revenue by Seller")
    fig, by_decile = _seller_fig(sellers)
    st.plotly_chart(fig)
    takeaway(f"The top 10% of sellers generate {by_decile.iloc[0]['share']:.0%} of revenue.", label="Insight")

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
