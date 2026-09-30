import streamlit as st

from src.kpis import KPIS, fmt_target, fmt_value, reporting_periods, scorecard
from src.sections import modeling, quality, schema


def _kpi_definitions() -> None:
    periods = reporting_periods()
    card = scorecard()
    st.markdown(
        f"All KPIs compare **{periods['label']}** with **{periods['prior_label']}**. The dataset has no official "
        "targets - the targets below are proposed by Data Intelligence and should be confirmed with each KPI owner."
    )
    st.dataframe(
        [
            {
                "KPI": k.label,
                "Definition": k.definition,
                "Target": fmt_target(k),
                periods["prior_label"]: fmt_value(k, card.loc[k.key, "prior"]),
                periods["label"]: fmt_value(k, card.loc[k.key, "current"]),
                "Status": card.loc[k.key, "status"],
                "Why it matters": k.meaning.split(" Target")[0],
            }
            for k in KPIS
        ],
        width="stretch",
        hide_index=True,
    )
    st.caption("Status: On track = meets target; Watch = misses by less than 10% of the target; "
               "Off track = misses by more. Growth KPIs are judged on their YoY change.")


def render() -> None:
    st.markdown("How the numbers in this report were built, and why they can be trusted.")
    tabs = st.tabs(["KPI definitions & targets", "Data schema", "Data quality", "Cleaning & modeling"])
    for tab, fn in zip(tabs, [_kpi_definitions, schema.render, quality.render, modeling.render]):
        with tab:
            fn()
