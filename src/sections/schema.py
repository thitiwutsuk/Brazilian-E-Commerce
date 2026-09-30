import streamlit as st

from src.data_loader import load_raw
from src.schema import TABLES, build_dot, build_flow_dot, column_profile, relationship_stats, table_catalog
from src.theme import key_findings


def render() -> None:
    catalog = table_catalog()
    rels = relationship_stats().set_index("Child → Parent")
    customers = load_raw("customers")

    st.markdown(
        f"The report is built from **{len(catalog)} source files ({catalog['Rows'].sum() / 1e6:.2f}M rows)** from "
        "Olist's order system. Every step from raw file to chart is code, so the report can be rebuilt in one run."
    )

    st.subheader("How data flows into this report")
    st.graphviz_chart(build_flow_dot(), width="stretch")

    st.subheader("What each source contains")
    st.dataframe(
        catalog[["Table", "Description", "Grain", "Rows"]].rename(columns={"Grain": "One row is"}),
        width="stretch",
        hide_index=True,
        column_config={"Rows": st.column_config.NumberColumn(format="localized")},
    )

    st.subheader("How the tables connect")
    st.caption("Orders sit at the centre; every other table links to them through a shared ID. "
               "Dark green = transactions, light green = descriptive data, grey = reference data.")
    st.graphviz_chart(build_dot(), width="stretch")

    with st.expander("Look at the raw data"):
        name = st.selectbox("Table", list(TABLES), format_func=lambda n: f"{n} - {TABLES[n]['desc']}")
        st.dataframe(load_raw(name).head(10), width="stretch", hide_index=True)
        st.dataframe(
            column_profile(name),
            width="stretch",
            hide_index=True,
            column_config={
                "Non-null": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                "Distinct values": st.column_config.NumberColumn(format="localized"),
            },
        )

    key_findings(
        [
            f"**The links between tables are reliable** - every order, product and seller ID matches its source "
            f"({rels.loc['order_items.order_id → orders', 'Match rate']:.0%}), so no sales are lost when combining them.",
            "**One order can hold several items, so order totals must not be added up item by item** - doing so "
            "double-counts revenue (see *Cleaning & modeling*).",
            f"**A customer is identified by `customer_unique_id`**, not `customer_id` (which is new for every order): "
            f"{customers['customer_id'].nunique():,} order IDs belong to {customers['customer_unique_id'].nunique():,} "
            "real people.",
        ],
    )
