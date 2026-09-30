import streamlit as st

from src.kpis import KPIS, reporting_periods, scorecard
from src.sections import modeling, quality, schema


def _kpi_definitions() -> None:
    periods = reporting_periods()
    card = scorecard()
    st.markdown(
        f"All KPIs compare **{periods['label']}** with **{periods['prior_label']}**. Values and targets are shown "
        "on the KPI cards. The dataset has no official targets - they are proposed in this report and "
        "should be confirmed with each KPI owner."
    )
    st.dataframe(
        [
            {
                "KPI": k.label,
                "Definition": k.definition,
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
    tabs = st.tabs(["KPI definitions", "Data architecture", "Data quality", "Cleaning & modeling"])
    for tab, fn in zip(tabs, [_kpi_definitions, schema.render, quality.render, modeling.render]):
        with tab:
            fn()
