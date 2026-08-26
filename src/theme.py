import plotly.express as px
import streamlit as st

BRAND_COLOR = "#2a78d6"
ACCENT_RED = "#e34948"
NEUTRAL_GREY = "#898781"
CHART_FONT = "sans-serif"

COLOR_RAMP = ["#2a78d6", "#104281", "#6da7ec", "#00335c", "#cde2fb", "#5a80ac"]
SEQUENTIAL_BLUE = ["#cde2fb", "#6da7ec", "#2a78d6", "#104281"]
DIVERGING_SCALE = [ACCENT_RED, NEUTRAL_GREY, BRAND_COLOR]
SCORE_COLOR = {1: ACCENT_RED, 2: "#c46f68", 3: NEUTRAL_GREY, 4: "#5a80ac", 5: BRAND_COLOR}


def configure_page(title: str, icon: str, layout: str = "wide") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout=layout)
    px.defaults.template = "plotly_white"
    px.defaults.color_discrete_sequence = COLOR_RAMP


def style_fig(fig):
    fig.update_layout(template="plotly_white", font_family=CHART_FONT)
    return fig
