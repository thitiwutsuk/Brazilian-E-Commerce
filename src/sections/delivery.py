import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.kpis import KPI_BY_KEY, monthly_kpis, render_cards, scorecard
from src.story import QUESTIONS, annotate_crises, crisis_months, highlight_crises, question_label
from src.metrics import LOW_SCORE, delivered_orders, late_vs_on_time
from src.theme import ACCENT_RED, BRAND_COLOR, INK, key_findings, section_header, style_fig, takeaway

DELAY_BUCKETS = [
    (-999, 0, "ตรงเวลาหรือเร็วกว่า"),
    (1, 3, "ช้า 1–3 วัน"),
    (4, 7, "ช้า 4–7 วัน"),
    (8, 999, "ช้า 8 วันขึ้นไป"),
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
    fig.add_scatter(x=mk["month"], y=mk["late"] * 100, name="อัตราส่งช้า (%)", mode="lines+markers",
                    line=dict(color=ACCENT_RED, width=3))
    fig.add_scatter(x=mk["month"], y=mk["negative"] * 100, name=f"รีวิว 1–{LOW_SCORE} ดาว (%)",
                    mode="lines+markers", line=dict(color=INK, width=2))
    fig.add_hline(y=KPI_BY_KEY["late"].target * 100, line_dash="dot", line_color=ACCENT_RED,
                  annotation_text=f"เป้าอัตราส่งช้า {KPI_BY_KEY['late'].target:.0%}", annotation_position="top left")
    highlight_crises(fig)
    annotate_crises(fig, below=True)
    fig.update_layout(title="อัตราส่งช้าเทียบกับรีวิวแย่ รายเดือน", yaxis_title="%",
                      legend=dict(orientation="h", y=1.08, x=1, xanchor="right"), hovermode="x unified")
    return style_fig(fig)


def _impact_fig(by_bucket: pd.DataFrame):
    is_late = by_bucket["bucket"].astype(str).str.startswith("ช้า")
    fig = px.bar(by_bucket, x="bucket", y="negative", title="ยิ่งส่งช้า รีวิวยิ่งแย่",
                 labels={"bucket": "", "negative": f"% order ที่ได้ 1–{LOW_SCORE} ดาว"},
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

    st.subheader("1. ภาพรวมประสบการณ์ลูกค้า")
    render_cards(["late", "negative", "review", "delivery_days"])
    takeaway(f"ส่งช้าเพิ่มเกินเท่าตัว ({card.loc['late', 'prior']:.1%} → {card.loc['late', 'current']:.1%}) "
             "ทั้งที่เวลาจัดส่งเฉลี่ยเท่าเดิม")

    st.subheader("2. แนวโน้มการจัดส่งรายเดือน")
    st.plotly_chart(_trend_fig())
    takeaway("ส่งช้าพุ่งขึ้นช่วงยอดพีค และรีวิวแย่พุ่งตามไปด้วย")

    st.subheader("3. ผลกระทบต่อรีวิวลูกค้า")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_impact_fig(by_bucket))
    with col2:
        with st.container(border=True):
            st.metric(f"รีวิว 1–{LOW_SCORE} ดาว: ส่งช้า vs. ตรงเวลา",
                      f"{late['negative_share']:.0%} vs. {on_time['negative_share']:.0%}")
        with st.container(border=True):
            st.metric("โอกาสได้รีวิวแย่เมื่อส่งช้า", f"{risk:.1f} เท่า")

    key_findings(
        [
            f"**ตามการเติบโตไม่ทัน:** อัตราส่งช้าเพิ่มเป็น {card.loc['late', 'current']:.1%} "
            f"(เป้า {KPI_BY_KEY['late'].target:.0%})",
            f"**ช่วงพีคระบบรับไม่ไหว:** {', '.join(f'{m:%b %Y} ({v:.0%})' for m, v in zip(crisis['month'], crisis['late']))}",
            f"**ส่งช้า = ลูกค้าไม่พอใจ:** order ที่ส่งช้ามีโอกาสได้รีวิว 1–{LOW_SCORE} ดาวมากกว่า {risk:.1f} เท่า",
        ],
        so_what="รักษาวันส่งที่สัญญากับลูกค้า โดยเฉพาะช่วงยอดพีค",
        lang="th",
    )
