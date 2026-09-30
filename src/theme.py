import plotly.express as px
import streamlit as st

BRAND_COLOR = "#06C755"
ACCENT_RED = "#e34948"
NEUTRAL_GREY = "#898781"
INK = "#1E1E1E"
GRID_GREY = "#E5E5E5"
CHART_FONT = "sans-serif"

COLOR_RAMP = ["#06C755", "#00893D", "#7ED9A8", "#003A1F", "#B6EFCB", "#00B14F"]
SEQUENTIAL_GREEN = ["#B6EFCB", "#7ED9A8", "#06C755", "#00893D"]

# Monotone green ramp for review scores (1 = lightest, 5 = brand color) - keeps
# the Reviews page in the same single color family as the rest of the app
# instead of a red/green good-bad diverging scale.
SCORE_COLOR = {1: "#B6EFCB", 2: "#7ED9A8", 3: "#3FCB84", 4: "#00B14F", 5: BRAND_COLOR}
SCORE_SCALE = ["#B6EFCB", "#7ED9A8", "#3FCB84", "#00B14F", BRAND_COLOR]


def configure_page(title: str, layout: str = "wide") -> None:
    st.set_page_config(page_title=title, layout=layout)
    px.defaults.template = "plotly_white"
    px.defaults.color_discrete_sequence = COLOR_RAMP


def style_fig(fig):
    """Bold, low-clutter chart style: big readable labels, thin gridlines,
    outlined bars - values should read at a glance without checking the axis."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family=CHART_FONT, size=13, color=INK),
        margin=dict(t=60, l=10, r=10, b=10),
    )
    # Only style the title font if a title is actually set - Plotly's map
    # renderer prints the literal string "undefined" as a title-like overlay
    # when title_font is set on a figure with no title text (hit on the geo
    # map page, which has no chart title).
    if fig.layout.title.text:
        fig.update_layout(title_font=dict(family=CHART_FONT, size=18, color=INK))
    fig.update_xaxes(showgrid=False, linecolor=INK, linewidth=1, ticks="outside", tickcolor=INK)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_GREY, zeroline=False, linecolor=INK, linewidth=1)
    fig.update_traces(marker_line_color=INK, marker_line_width=1, selector=dict(type="bar"))
    fig.update_traces(marker_line_color=INK, marker_line_width=1, selector=dict(type="histogram"))
    fig.update_traces(textfont_size=14, textfont_color=INK, selector=dict(type="bar"))
    fig.update_traces(line_width=3, selector=dict(type="scatter", mode="lines+markers"))
    return fig


def section_header(question: str, method: str) -> None:
    """Opening of every report tab: the question it answers and how."""
    st.markdown(f"**Question.** {question}")
    st.caption(f"Method: {method}")


def key_findings(findings: list, so_what: str = "") -> None:
    """Closing box of every report tab: numbered findings + the implication."""
    # Escape "$" so two money amounts in one line aren't rendered as LaTeX math.
    findings = [f.replace("$", "\\$") for f in findings]
    so_what = so_what.replace("$", "\\$")
    with st.container(border=True):
        st.markdown("#### Key findings")
        st.markdown("\n".join(f"{i}. {f}" for i, f in enumerate(findings, 1)))
        if so_what:
            st.markdown(f"**What this means for us:** {so_what}")


STATUS_STYLE = {
    "On track": ("#E6F9EE", "#00893D"),
    "Watch": ("#FFF4D6", "#8A6100"),
    "Off track": ("#FDE7E7", "#B42318"),
}


def status_badge(status: str) -> str:
    bg, fg = STATUS_STYLE[status]
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;'
            f'font-size:0.8rem;font-weight:600;white-space:nowrap">{status}</span>')


def kpi_card(label, value, delta, higher_is_better, status, target, meaning, help) -> None:
    with st.container(border=True):
        st.metric(label, value, delta, delta_color="normal" if higher_is_better else "inverse", help=help)
        st.markdown(
            f'{status_badge(status)} <span style="color:{NEUTRAL_GREY};font-size:0.8rem">Target {target}</span>',
            unsafe_allow_html=True,
        )
        st.caption(meaning)


def takeaway(text: str) -> None:
    """One-line "what this means" under a chart, in plain business language."""
    st.markdown(f"**What this means:** {text.replace('$', chr(92) + '$')}")
