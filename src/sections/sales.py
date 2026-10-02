import pandas as pd
import plotly.express as px
import streamlit as st

from src.currency import get_currency
from src.kpis import render_cards, reporting_periods, scorecard
from src.metrics import category_pareto, monthly_sales, n_for_share, peak_day, seller_pareto, yoy_growth
from src.story import QUESTIONS, question_label
from src.theme import BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

TOP_CATEGORIES = 10


def _trend_fig(m: pd.DataFrame, yoy: dict, peak_d: pd.Series):
    df = m.assign(year=m["month"].dt.year.astype(str), month_name=m["month"].dt.strftime("%b"))
    this_year = m[m["month"].dt.year == yoy["year"]]
    peak_m = m.loc[m["orders"].idxmax()]
    fig = px.line(df, x="month_name", y="orders", color="year", markers=True, title="จำนวน order รายเดือน เทียบปีต่อปี",
                  labels={"orders": "จำนวน order", "month_name": "", "year": ""},
                  color_discrete_map={str(yoy["year"] - 1): NEUTRAL_GREY, str(yoy["year"]): BRAND_COLOR})
    fig.update_xaxes(categoryorder="array", categoryarray=pd.date_range("2000-01-01", periods=12, freq="MS").strftime("%b"))
    fig.add_hrect(y0=this_year["orders"].min(), y1=this_year["orders"].max(), fillcolor=BRAND_COLOR, opacity=0.08,
                  line_width=0, annotation_text=f"{yoy['year']}: {this_year['orders'].min() / 1000:.1f}–"
                  f"{this_year['orders'].max() / 1000:.1f}K ต่อเดือน", annotation_position="bottom left")
    fig.add_annotation(x=f"{peak_m['month']:%b}", y=peak_m["orders"], showarrow=True, arrowhead=0, ax=-60, ay=-40,
                       text=f"<b>Black Friday {peak_m['month']:%Y}</b><br>{int(peak_d['orders']):,} order ในวันเดียว "
                            f"({peak_d['orders'] / peak_d['median']:.0f} เท่าของวันปกติ)")
    fig.update_layout(legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
                      yaxis_range=[0, df["orders"].max() * 1.25])
    return style_fig(fig), this_year


def _volume_share(card: pd.DataFrame) -> float:
    """Share of the GMV change explained by more orders (at last year's order value)."""
    volume = (card.loc["orders", "current"] - card.loc["orders", "prior"]) * card.loc["aov", "prior"]
    return volume / (card.loc["gmv", "current"] - card.loc["gmv", "prior"])


def _category_fig(cats: pd.DataFrame):
    top = cats.head(TOP_CATEGORIES).iloc[::-1]
    fig = px.bar(top, x=top["share"] * 100, y="product_category_name_english", orientation="h",
                 title=f"สัดส่วนรายได้ {TOP_CATEGORIES} หมวดสินค้าแรก",
                 labels={"x": "สัดส่วนรายได้ (%)", "product_category_name_english": ""},
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

    st.subheader("1. ภาพรวมการเติบโต")
    render_cards(["gmv", "orders", "aov", "customers"])
    takeaway(f"GMV ที่โต {volume_share:.0%} มาจากจำนวน order ที่เพิ่มขึ้น มูลค่าต่อ order แทบไม่เปลี่ยน")

    st.subheader("2. แนวโน้ม order รายเดือน")
    fig, this_year = _trend_fig(m, yoy, peak_d)
    st.plotly_chart(fig)
    takeaway(f"ยอดกระโดดขึ้นครั้งเดียวช่วง Black Friday {yoy['year'] - 1} แล้วทรงตัวตลอดปี {yoy['year']}")
    with st.expander("ข้อมูลรายเดือน"):
        st.dataframe(
            m.assign(revenue=m["revenue"] / rate),
            width="stretch",
            hide_index=True,
            column_config={
                "month": st.column_config.DateColumn("เดือน", format="MMM YYYY"),
                "orders": st.column_config.NumberColumn("จำนวน order", format="localized"),
                "revenue": st.column_config.NumberColumn(f"GMV ({symbol})", format="dollar"),
                "orders_mom": st.column_config.NumberColumn("Orders MoM", format="percent"),
                "revenue_mom": st.column_config.NumberColumn("GMV MoM", format="percent"),
            },
        )

    st.subheader("3. รายได้กระจุกตัวที่ไหน")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_category_fig(cats))
    with col2:
        with st.container(border=True):
            st.metric("จำนวนหมวดที่สร้างรายได้ 80%", f"{n80} จาก {len(cats)}")
        with st.container(border=True):
            st.metric("รายได้จาก seller top 10%", f"{top_sellers_share:.0%}")

    key_findings(
        [
            f"**โตจริง แต่หยุดเร่งแล้ว:** GMV {card.loc['gmv', 'change']:+.0%} YoY แต่ปี {yoy['year']} ทรงตัวที่ "
            f"{this_year['orders'].min() / 1000:.1f}–{this_year['orders'].max() / 1000:.1f}K order ต่อเดือน",
            f"**โตจากจำนวน order:** {volume_share:.0%} ของการเติบโตมาจาก order ที่เพิ่มขึ้น "
            f"มูลค่าต่อ order แทบไม่เปลี่ยน ({card.loc['aov', 'change']:+.0%})",
            f"**รายได้กระจุกตัว:** {n80} หมวดสินค้า และ seller top 10% สร้างรายได้ส่วนใหญ่",
        ],
        so_what=f"ดูแลหมวดและ seller หลัก และวางแผนรับยอดช่วง Black Friday {periods['as_of'].year}",
        lang="th",
    )
