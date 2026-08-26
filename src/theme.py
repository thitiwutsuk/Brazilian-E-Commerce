import plotly.express as px
import streamlit as st

BRAND_COLOR = "#06C755"
ACCENT_RED = "#e34948"
NEUTRAL_GREY = "#898781"
CHART_FONT = "sans-serif"

COLOR_RAMP = ["#06C755", "#00893D", "#7ED9A8", "#003A1F", "#B6EFCB", "#00B14F"]
SEQUENTIAL_GREEN = ["#B6EFCB", "#7ED9A8", "#06C755", "#00893D"]
DIVERGING_SCALE = [ACCENT_RED, NEUTRAL_GREY, BRAND_COLOR]
SCORE_COLOR = {1: ACCENT_RED, 2: "#c46f68", 3: NEUTRAL_GREY, 4: "#5cae7e", 5: BRAND_COLOR}


def configure_page(title: str, icon: str, layout: str = "wide") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout=layout)
    px.defaults.template = "plotly_white"
    px.defaults.color_discrete_sequence = COLOR_RAMP


def style_fig(fig):
    fig.update_layout(template="plotly_white", font_family=CHART_FONT)
    return fig
