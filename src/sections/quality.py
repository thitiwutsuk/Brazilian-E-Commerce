import plotly.express as px
import streamlit as st

from src.currency import fmt_money_short
from src.quality import MIN_ORDERS_PER_MONTH, RECON_ABS_TOLERANCE, analysis_window, monthly_coverage, reconcile_payments, run_checks
from src.theme import ACCENT_RED, BRAND_COLOR, NEUTRAL_GREY, key_findings, section_header, style_fig

STATUS_COLOR = {"PASS": "#B6EFCB", "WARN": "#FFE8A3", "FAIL": "#F8C4C3"}


def render() -> None:
    section_header(
        "Can the data be trusted, and what has to be fixed or excluded before analysis?",
        "Automated checks across six quality dimensions (uniqueness, completeness, referential integrity, "
        "validity, accuracy, timeliness). Status: PASS = no issue, WARN = issue within tolerance, "
        "FAIL = above tolerance.",
    )

    checks = run_checks()
    counts = checks["Status"].value_counts()
    col1, col2, col3 = st.columns(3)
    col1.metric("PASS", counts.get("PASS", 0))
    col2.metric("WARN", counts.get("WARN", 0))
    col3.metric("FAIL", counts.get("FAIL", 0))

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

    st.subheader("Timeliness: monthly coverage")
    cov = monthly_coverage()
    start, end = analysis_window()
    fig = px.bar(cov, x="month", y="orders", title="Orders per month (full calendar spine)",
                 labels={"month": "", "orders": "Orders"})
    fig.update_traces(marker_color=[BRAND_COLOR if w else NEUTRAL_GREY for w in cov["in_window"]])
    fig.add_hline(y=MIN_ORDERS_PER_MONTH, line_dash="dot", line_color=ACCENT_RED,
                  annotation_text=f"{MIN_ORDERS_PER_MONTH} orders", annotation_position="top left")
    st.plotly_chart(style_fig(fig))
    st.caption(f"Green = analysis window ({start:%b %Y} – {end:%b %Y}); grey = partial months excluded from trends.")

    st.subheader("Accuracy: payment reconciliation")
    recon = reconcile_payments()
    off = recon[~recon["within_tolerance"]]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Orders reconciled", f"{len(recon):,}")
    col2.metric("Total paid", fmt_money_short(recon["payment_value"].sum()))
    col3.metric("Items + freight", fmt_money_short(recon["item_total"].sum()))
    col4.metric(f"Outside ±R${RECON_ABS_TOLERANCE:.0f}", f"{len(off):,}", f"{len(off) / len(recon):.2%} of orders",
                delta_color="off")
    fig_off = px.histogram(off, x="diff", nbins=40, title="Paid minus items + freight, mismatched orders only (R$)",
                           labels={"diff": "Difference (R$)"})
    fig_off.update_traces(marker_color=BRAND_COLOR)
    st.plotly_chart(style_fig(fig_off))

    gap_months = cov.loc[cov["orders"] == 0, "month"]
    edge = cov[~cov["in_window"]]
    status = checks.set_index("Check")
    key_findings(
        [
            f"**{counts.get('PASS', 0)} of {len(checks)} checks pass, {counts.get('WARN', 0)} are within tolerance and "
            f"{counts.get('FAIL', 0)} fails** (the missing month below). Core business fields - prices, review scores, "
            "delivery dates - have no invalid values; every issue found is about gaps or duplicates.",
            f"**Coverage is uneven at both ends.** {', '.join(f'{m:%b %Y}' for m in gap_months)} has zero orders and "
            f"{len(edge)} edge months have under {MIN_ORDERS_PER_MONTH} orders "
            f"({edge['orders'].sum():,} orders in total). Trend analysis is limited to "
            f"**{start:%b %Y} – {end:%b %Y}** so partial months don't read as crashes.",
            f"**{status.loc['Every order has at least one item', 'Count']:,} orders have no items** - almost all are "
            "`unavailable` or `canceled`. They count as orders but carry no product revenue.",
            f"**{status.loc['Products have a category', 'Count']:,} products have no category** "
            f"({status.loc['Products have a category', 'Rate']:.1%}); they are kept as '(unknown)' rather than dropped, "
            "so category totals still add up to total revenue.",
            f"**Payments reconcile with items + freight:** totals differ by "
            f"{recon['payment_value'].sum() / recon['item_total'].sum() - 1:.2%} and only {len(off):,} orders "
            f"({len(off) / len(recon):.2%}) are off by more than R${RECON_ABS_TOLERANCE:.0f}. "
            f"{(off['diff'] > 0).mean():.0%} of those gaps are positive (customer paid more, median "
            f"R${off['diff'].median():.2f}), consistent with installment interest rather than missing data.",
        ],
        so_what="The data is fit for analysis once three rules are applied: dedupe reviews, keep unknown categories, "
        "and restrict trends to fully covered months.",
    )
