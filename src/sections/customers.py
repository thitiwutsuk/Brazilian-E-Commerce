import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import load_raw
from src.kpis import period_slice, render_cards, reporting_periods, scorecard
from src.metrics import orders_per_customer
from src.story import question_label
from src.theme import BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig, takeaway

TOP_STATES = 8


def _loyalty_fig(freq: pd.Series):
    dist = freq.clip(upper=4).value_counts().sort_index().rename(index={4: "4+"})
    dist = dist.rename_axis("orders").reset_index(name="customers")
    dist["orders"] = dist["orders"].astype(str).map(lambda n: f"ซื้อ {n} ครั้ง")
    dist["pct"] = dist["customers"] / dist["customers"].sum() * 100
    fig = px.bar(dist, x="orders", y="pct", title="ลูกค้าแบ่งตามจำนวนครั้งที่ซื้อ",
                 labels={"orders": "", "pct": "% ของลูกค้า"}, text=dist["pct"].map(lambda v: f"{v:.1f}%"))
    fig.update_traces(marker_color=[BRAND_COLOR] + [NEUTRAL_GREY] * (len(dist) - 1), textposition="outside")
    fig.update_yaxes(range=[0, 110])
    return style_fig(fig)


def _state_fig(share: pd.Series, label: str):
    top = share.head(TOP_STATES).iloc[::-1] * 100
    fig = px.bar(x=top.values, y=top.index, orientation="h", title=f"สัดส่วน order ราย state ({TOP_STATES} อันดับแรก, {label})",
                 labels={"x": "สัดส่วน order (%)", "y": ""}, text=[f"{v:.0f}%" for v in top.values])
    fig.update_traces(marker_color=[NEUTRAL_GREY] * (len(top) - 3) + [BRAND_COLOR] * 3, textposition="outside")
    fig.update_layout(xaxis_range=[0, top.max() * 1.2])
    return style_fig(fig)


def render() -> None:
    section_header(f"{question_label(1, 2)} · ลูกค้าของเราเป็นใคร และอยู่ที่ไหน?")
    periods = reporting_periods()
    card = scorecard()
    freq = orders_per_customer()
    cur = period_slice("current")
    share = cur["customer_state"].value_counts(normalize=True)
    top3 = share.head(3)
    sellers = load_raw("sellers")
    seller_share = (sellers["seller_state"] == share.index[0]).mean()

    st.subheader("1. ภาพรวมลูกค้า")
    render_cards(["customers", "returning"], per_row=2)
    takeaway(f"ฐานลูกค้าโต {card.loc['customers', 'change']:+.0%} แต่เกือบทั้งหมดเป็นลูกค้าที่ซื้อครั้งแรก")

    st.subheader("2. การกลับมาซื้อซ้ำ")
    st.plotly_chart(_loyalty_fig(freq))
    takeaway(f"ลูกค้า {(freq == 1).mean():.0%} ซื้อแค่ครั้งเดียว")

    st.subheader("3. ลูกค้ากระจุกตัวที่ไหน")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.plotly_chart(_state_fig(share, periods["label"]))
    with col2:
        with st.container(border=True):
            st.metric(f"order จาก {', '.join(top3.index)}", f"{top3.sum():.0%}")
        with st.container(border=True):
            st.metric(f"seller ที่อยู่ใน {share.index[0]}", f"{seller_share:.0%}")

    key_findings(
        [
            f"**โตจากลูกค้าใหม่:** ลูกค้า {(freq == 1).mean():.0%} ซื้อครั้งเดียว และ order จากลูกค้าเก่ามีแค่ "
            f"{card.loc['returning', 'current']:.1%}",
            f"**ลูกค้ากระจุกตัว:** {', '.join(top3.index)} รวมกันเป็น {top3.sum():.0%} ของ order",
            f"**seller ก็กระจุกตัว:** seller {seller_share:.0%} อยู่ใน {share.index[0]} ไกลจากลูกค้าหลายพื้นที่",
        ],
        so_what="กระตุ้นให้ลูกค้ากลับมาซื้อซ้ำ และขยายการเข้าถึงและการจัดส่งนอกภาคตะวันออกเฉียงใต้",
        lang="th",
    )
