import streamlit as st

from src.data_loader import load_item_level, load_order_level
from src.kpis import reporting_periods
from src.sections import appendix, customers, delivery, recommendations, sales, summary
from src.theme import configure_page

configure_page("รายงานผลการดำเนินงาน Olist")
st.title("รายงานผลการดำเนินงาน Olist Marketplace")
st.caption(f"สรุปผลการดำเนินงาน {reporting_periods()['label']}")

# Warm the cache once so every tab reads the same prepared tables.
load_order_level()
load_item_level()

SECTIONS = [
    ("สรุปผู้บริหาร", summary),
    ("ยอดขายและการเติบโต", sales),
    ("ประสบการณ์ลูกค้า", delivery),
    ("ข้อเสนอแนะ", recommendations),
    ("ลูกค้าและตลาด", customers),
    ("Appendix", appendix),
]

for tab, (_, section) in zip(st.tabs([name for name, _ in SECTIONS]), SECTIONS):
    with tab:
        section.render()
