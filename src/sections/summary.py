import plotly.graph_objects as go
import streamlit as st

from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, reporting_periods
from src.story import QUESTIONS, annotate_crises, crisis_months
from src.theme import ACCENT_RED, GRID_GREY, INK, style_fig, takeaway


def _growth_vs_reliability_fig():
    m = monthly_kpis()
    late_target = KPI_BY_KEY["late"].target
    fig = go.Figure()
    fig.add_bar(x=m["month"], y=m["orders"], name="จำนวน order", marker_color=GRID_GREY, marker_line_width=0)
    fig.add_scatter(x=m["month"], y=m["late"] * 100, name="อัตราส่งช้า (%)", yaxis="y2",
                    mode="lines+markers", line=dict(color=ACCENT_RED, width=3))
    fig.add_scatter(x=m["month"], y=[late_target * 100] * len(m), name=f"เป้าอัตราส่งช้า ({late_target:.0%})",
                    yaxis="y2", mode="lines", line=dict(color=INK, dash="dot", width=1))
    fig.update_layout(
        title="จำนวน order เทียบกับอัตราส่งช้า รายเดือน",
        yaxis=dict(title="จำนวน order", showgrid=False),
        yaxis2=dict(title="อัตราส่งช้า (%)", overlaying="y", side="right", rangemode="tozero", showgrid=True,
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
        st.markdown("#### บริบทและคำถามหลัก")
        st.markdown(
            "Olist โตเร็วมากในปี 2017–2018 คำถามสำคัญคือ **การเติบโตนี้แข็งแรงหรือไม่** "
            f"และอีก 3 เดือนจะถึง Black Friday {periods['as_of'].year} ซึ่งเป็นช่วงขายดีที่สุดของปี "
            "รายงานนี้จึงตอบ 3 คำถาม:"
        )
        where = {1: "ยอดขายและการเติบโต, ลูกค้าและตลาด", 2: "ประสบการณ์ลูกค้า", 3: "ข้อเสนอแนะ"}
        st.markdown("\n".join(f"{n}. **{q}** *(→ {where[n]})*" for n, q in QUESTIONS.items()))

    st.subheader(f"สรุปผลตาม KPI · {periods['label']} เทียบ {periods['prior_label']}")
    st.caption("ชี้ที่ ⓘ เพื่อดูคำนิยามของแต่ละ KPI · เป้าหมายเป็นค่าที่เสนอ ไม่ใช่เป้าทางการ")
    st.markdown("**การเติบโต**")
    render_cards(["gmv", "orders", "aov", "customers"])
    st.markdown("**ประสบการณ์ลูกค้า**")
    render_cards(["late", "negative", "review", "returning"])

    st.subheader("ข้อค้นพบหลัก: การจัดส่งรับช่วงพีคไม่ไหว")
    st.plotly_chart(_growth_vs_reliability_fig())
    normal = monthly.loc[monthly.index < crisis.index.min(), "late"].median()
    takeaway(
        f"เดือนปกติส่งช้าราว {normal:.0%} แต่ช่วงยอดพีคพุ่งเป็น "
        f"{', '.join(f'{r.late:.0%} ({m:%b %Y})' for m, r in crisis.iterrows())} "
        f"ตอนนี้กลับมาเฉลี่ย {last3['late'].mean():.1%} ใน 3 เดือนล่าสุด "
        "ระบบรับยอดปกติได้ แต่รับช่วงพีคไม่ไหว ต้องแก้ก่อนเดือนพฤศจิกายน",
        label="ความหมายต่อธุรกิจ",
    )
