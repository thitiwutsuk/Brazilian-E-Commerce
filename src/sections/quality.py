import plotly.express as px
import streamlit as st

from src.quality import MIN_ORDERS_PER_MONTH, RECON_ABS_TOLERANCE, analysis_window, monthly_coverage, reconcile_payments, run_checks
from src.theme import BRAND_COLOR, NEUTRAL_GREY, key_findings, style_fig

STATUS_COLOR = {"PASS": "#B6EFCB", "WARN": "#FFE8A3", "FAIL": "#F8C4C3"}


def render() -> None:
    checks = run_checks()
    counts = checks["Status"].value_counts()
    recon = reconcile_payments()
    off = recon[~recon["within_tolerance"]]
    start, end = analysis_window()

    with st.container(border=True):
        st.markdown(
            f"**Verdict: the data is fit for decision-making.** {len(checks)} automated checks run every time the "
            f"report is built - {counts.get('PASS', 0)} pass, {counts.get('WARN', 0)} find small issues that are "
            f"handled, {counts.get('FAIL', 0)} needs a rule (a month with no data). Payments match item prices + "
            f"freight to within **{abs(recon['payment_value'].sum() / recon['item_total'].sum() - 1):.2%}**."
        )

    st.subheader("Issues found and how they were handled")
    issues = checks[checks["Status"] != "PASS"].sort_values("Rate", ascending=False)
    st.dataframe(
        issues[["Check", "Count", "Rate", "Action"]].assign(Rate=issues["Rate"] * 100).rename(
            columns={"Check": "What we checked", "Count": "Rows affected", "Action": "How it was handled"}
        ),
        width="stretch",
        height=(len(issues) + 1) * 35 + 3,  # show every issue without scrolling
        hide_index=True,
        column_config={
            "Rate": st.column_config.NumberColumn("% of rows", format="%.2f%%"),
            "Rows affected": st.column_config.NumberColumn(format="localized"),
        },
    )

    st.subheader("Why trends start in Jan 2017")
    cov = monthly_coverage()
    fig = px.bar(cov, x="month", y="orders", title="Orders per month in the raw data",
                 labels={"month": "", "orders": "Orders"})
    fig.update_traces(marker_color=[BRAND_COLOR if w else NEUTRAL_GREY for w in cov["in_window"]])
    st.plotly_chart(style_fig(fig))
    st.caption(f"Grey months have fewer than {MIN_ORDERS_PER_MONTH} orders (partial data) and are left out of "
               f"trends, which cover {start:%b %Y} – {end:%b %Y}.")

    with st.expander(f"All {len(checks)} checks"):
        st.dataframe(
            checks.assign(Rate=checks["Rate"] * 100).style.map(
                lambda s: f"background-color: {STATUS_COLOR[s]}", subset=["Status"]
            ),
            width="stretch",
            height=(len(checks) + 1) * 35 + 3,  # show every check without scrolling
            hide_index=True,
            column_config={
                "Rate": st.column_config.NumberColumn("Rate (% of rows)", format="%.2f%%"),
                "Count": st.column_config.NumberColumn(format="localized"),
            },
        )

    status = checks.set_index("Check")
    row_issues = issues[issues["Check"] != "No gap months in the order timeline"]  # a month count, not rows
    key_findings(
        [
            "**No corrupt values** - prices, review scores and delivery dates are all valid; the issues are small "
            f"gaps and duplicates, none above {row_issues['Rate'].max():.1%} of rows.",
            f"**Every issue has a handling rule** - e.g. {status.loc['Products have a category', 'Count']:,} products "
            "without a category are kept as '(unknown)' so no revenue drops out of category totals.",
            f"**Money reconciles** - only {len(off):,} of {len(recon):,} orders ({len(off) / len(recon):.2%}) differ "
            f"from their items + freight by more than R${RECON_ABS_TOLERANCE:.0f}, mostly installment interest.",
        ],
    )
