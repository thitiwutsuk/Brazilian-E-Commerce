import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from src.currency import get_currency
from src.data_loader import load_order_level
from src.metrics import category_pareto, monthly_sales, n_for_share, peak_day, seller_pareto, yoy_growth
from src.kpis import render_cards, reporting_periods
from src.story import QUESTIONS, question_label
from src.theme import BRAND_COLOR, NEUTRAL_GREY, INK, key_findings, section_header, style_fig, takeaway


def _pareto_fig(p, label, top, title):
    symbol, rate = get_currency()
    head = p.head(top)
    fig = go.Figure()
    fig.add_bar(x=head[label], y=head["revenue"] / rate, name="Revenue", marker_color=BRAND_COLOR)
    fig.add_scatter(x=head[label], y=head["cum_share"] * 100, name="Cumulative %", yaxis="y2",
                    mode="lines+markers", line_color=INK)
    fig.update_layout(
        title=title,
        yaxis=dict(title=f"Revenue ({symbol})"),
        yaxis2=dict(title="Cumulative share (%)", overlaying="y", side="right", range=[0, 100], showgrid=False),
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        xaxis=dict(tickangle=-40),
    )
    return fig


def render() -> None:
    section_header(f"{question_label(1)} · {QUESTIONS[1]}")
    symbol, rate = get_currency()
    m = monthly_sales()
    yoy = yoy_growth()
    peak_m = m.loc[m["orders"].idxmax()]
    peak_d = peak_day()
    orders = load_order_level()
    window = orders[orders["month"].between(m["month"].min(), m["month"].max()) & (orders["order_status"] != "canceled")]

    render_cards(["gmv", "orders", "aov", "customers"])

    st.subheader("This year vs. last year")
    periods = reporting_periods()
    yoy_df = m.assign(year=m["month"].dt.year.astype(str), month_name=m["month"].dt.strftime("%b"))
    this_year = m[m["month"].dt.year == yoy["year"]]
    fig = px.line(yoy_df, x="month_name", y="orders", color="year", markers=True,
                  title="Monthly orders by year - a step up at Black Friday, then flat",
                  labels={"orders": "Orders", "month_name": "", "year": ""},
                  color_discrete_map={str(yoy["year"] - 1): NEUTRAL_GREY, str(yoy["year"]): BRAND_COLOR})
    fig.update_xaxes(categoryorder="array", categoryarray=pd.date_range("2000-01-01", periods=12, freq="MS").strftime("%b"))
    fig.add_hrect(y0=this_year["orders"].min(), y1=this_year["orders"].max(), fillcolor=BRAND_COLOR, opacity=0.08,
                  line_width=0, annotation_text=f"{yoy['year']}: flat at {this_year['orders'].min() / 1000:.1f}–"
                  f"{this_year['orders'].max() / 1000:.1f}K orders/month", annotation_position="bottom left")
    fig.add_annotation(x=f"{peak_m['month']:%b}", y=peak_m["orders"],
                       text=f"<b>Black Friday {peak_m['month']:%Y}</b><br>{peak_d['date']:%d %b}: "
                            f"{int(peak_d['orders']):,} orders in one day ({peak_d['orders'] / peak_d['median']:.0f}x normal)",
                       showarrow=True, arrowhead=0, ax=-60, ay=-40)
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
                      yaxis_range=[0, yoy_df["orders"].max() * 1.25])
    st.plotly_chart(style_fig(fig))
    takeaway(
        f"Every month of {yoy['year']} is well above the same month of {yoy['year'] - 1} "
        f"(orders {yoy['orders']:+.0%}, GMV {yoy['revenue']:+.0%} YoY for {periods['label']}), but the {yoy['year']} "
        f"line is flat at {this_year['orders'].min() / 1000:.1f}–{this_year['orders'].max() / 1000:.1f}K orders a "
        f"month. The growth came from one big step up around Black Friday {yoy['year'] - 1}, not from continued "
        "monthly growth this year."
    )

    table = m.assign(revenue=m["revenue"] / rate)
    with st.expander("Monthly table (orders, revenue, MoM %)"):
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                "month": st.column_config.DateColumn("Month", format="MMM YYYY"),
                "revenue": st.column_config.NumberColumn(f"Revenue ({symbol})", format="dollar"),
                "orders_mom": st.column_config.NumberColumn("Orders MoM", format="percent"),
                "revenue_mom": st.column_config.NumberColumn("Revenue MoM", format="percent"),
            },
        )

    st.subheader("Where the revenue comes from - and the concentration risk")
    cats = category_pareto()
    sellers = seller_pareto()
    n80 = n_for_share(cats)
    st.plotly_chart(style_fig(_pareto_fig(cats, "product_category_name_english", 25,
                                          "Revenue by category - top 25 with cumulative share")))
    takeaway(f"{n80} categories out of {len(cats)} bring in 80% of revenue. Stock-outs, price moves or delivery "
             f"problems in the top few ({', '.join(cats['product_category_name_english'].head(3))}) move the whole "
             "business - they deserve the closest monitoring.")

    col1, col2 = st.columns(2)
    with col1:
        deciles = sellers.assign(decile=(sellers["rank"] - 1) * 10 // len(sellers) + 1)
        by_decile = deciles.groupby("decile", as_index=False)["share"].sum()
        by_decile["pct"] = by_decile["share"] * 100
        fig_sel = px.bar(by_decile, x="decile", y="pct", title="Revenue share by seller decile",
                         labels={"decile": "Seller decile (1 = top 10%)", "pct": "Share of revenue (%)"},
                         text=by_decile["pct"].map(lambda v: f"{v:.0f}%"))
        fig_sel.update_traces(marker_color=[BRAND_COLOR] + [NEUTRAL_GREY] * 9, textposition="outside")
        fig_sel.update_xaxes(dtick=1)
        st.plotly_chart(style_fig(fig_sel))
    with col2:
        pay = window.groupby("payment_type", as_index=False)["payment_value"].sum()
        pay["pct"] = pay["payment_value"] / pay["payment_value"].sum() * 100
        pay = pay[pay["pct"] >= 0.1].sort_values("pct")
        fig_pay = px.bar(pay, x="pct", y="payment_type", orientation="h", title="Revenue by payment method",
                         labels={"pct": "Share of revenue (%)", "payment_type": ""},
                         text=pay["pct"].map(lambda v: f"{v:.0f}%"))
        fig_pay.update_traces(marker_color=BRAND_COLOR, textposition="outside")
        fig_pay.update_layout(xaxis_range=[0, pay["pct"].max() * 1.2])
        st.plotly_chart(style_fig(fig_pay))

    takeaway(f"The top 10% of sellers bring in {by_decile.iloc[0]['share']:.0%} of revenue - losing a handful of "
             f"them would hurt more than losing the bottom half. Credit card is the default way to pay, and "
             f"{window['payment_installments'].gt(1).mean():.0%} of orders are paid in installments.")

    freight_share = window["freight_value"].sum() / (window["item_price"].sum() + window["freight_value"].sum())
    installments = window["payment_installments"].gt(1).mean()
    key_findings(
        [
            f"**Black Friday is the single biggest event:** {peak_d['date']:%d %b %Y} had {int(peak_d['orders']):,} "
            f"orders - {peak_d['orders'] / peak_d['median']:.0f}x a median day - lifting {peak_m['month']:%B %Y} "
            f"{peak_m['orders_mom']:+.0%} MoM, the peak month of the period.",
            f"**Growth then plateaued.** Jan–Aug {yoy['year']} orders are {yoy['orders']:+.0%} YoY, but monthly volume "
            f"has stayed in a flat {this_year['orders'].min() / 1000:.1f}–{this_year['orders'].max() / 1000:.1f}K band "
            f"every month of {yoy['year']} - the 2017 scale-up phase is over.",
            f"**Category revenue is concentrated:** {n80} of {len(cats)} categories make 80% of revenue; the top "
            f"category ({cats.iloc[0]['product_category_name_english']}) alone is {cats.iloc[0]['share']:.0%}.",
            f"**Seller revenue is more concentrated still:** the top 10% of {len(sellers):,} sellers take "
            f"{by_decile.iloc[0]['share']:.0%} of revenue; the bottom half shares "
            f"{by_decile[by_decile['decile'] > 5]['share'].sum():.0%}.",
            f"**Credit card dominates** ({pay.set_index('payment_type').loc['credit_card', 'pct']:.0f}% of revenue) and "
            f"{installments:.0%} of orders pay in installments; freight is {freight_share:.0%} of what customers pay for items + shipping.",
        ],
        so_what="Growth is real but has levelled off. Black Friday is the biggest lever on volume, and a small "
        "set of categories and sellers carries the revenue - both need to be planned for and protected.",
    )
