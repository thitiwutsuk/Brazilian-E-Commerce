import streamlit as st

from src.data_loader import load_raw
from src.schema import TABLES, build_dot, build_flow_dot, column_profile, relationship_stats, table_catalog
from src.theme import key_findings, section_header


def render() -> None:
    section_header(
        "Where do the numbers in this report come from, what does the raw data look like, and how do the "
        "tables connect?",
        "Profiled all 9 source CSVs, declared primary/foreign keys, then measured every foreign key "
        "against its parent table (match rate, coverage, and fan-out).",
    )

    catalog = table_catalog()
    rels = relationship_stats().set_index("Child → Parent")

    st.subheader("Data flow")
    st.caption("From the raw files to this report. Every step is code, so the whole report rebuilds from the "
               "CSVs in one run.")
    st.graphviz_chart(build_flow_dot(), width="stretch")

    st.subheader("Raw data")
    st.caption("The source files exactly as delivered - pick a table to see its first rows and a profile of "
               "every column.")
    name = st.selectbox(
        "Table",
        list(TABLES),
        format_func=lambda n: f"{n} - {TABLES[n]['desc']}",
    )
    row = catalog.set_index("Table").loc[name]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", f"{row['Rows']:,}")
    col2.metric("Columns", row["Columns"])
    col3.metric("File size", f"{row['Size (MB)']} MB")
    col4.metric("Role", row["Role"])
    st.markdown(f"**Grain:** {row['Grain']} · **Primary key:** `{row['Primary key']}`")
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

    st.subheader("Data schema (entity-relationship diagram)")
    st.caption("Dark green = fact tables (events), light green = dimensions, grey = lookups. "
               "Crow's foot marks the 'many' side of each relationship.")
    st.graphviz_chart(build_dot(), width="stretch")

    st.subheader("Table catalog")
    st.dataframe(
        catalog.astype({"PK duplicates": "Int64"}),
        width="stretch",
        hide_index=True,
        column_config={"Rows": st.column_config.NumberColumn(format="localized")},
    )

    st.subheader("Relationship check")
    st.caption("Match rate = child keys found in the parent. Parents with ≥1 child = how much of the "
               "parent table is actually referenced. Max children per key = worst-case join fan-out.")
    st.dataframe(
        rels,
        width="stretch",
        column_config={
            "Match rate": st.column_config.NumberColumn(format="percent"),
            "Parents with ≥1 child": st.column_config.NumberColumn(format="percent"),
            "Child rows": st.column_config.NumberColumn(format="localized"),
        },
    )

    items_per_order = load_raw("order_items").groupby("order_id").size()
    customers = load_raw("customers")
    reviews = load_raw("order_reviews")
    geo = load_raw("geolocation")
    item_fk = rels.loc["order_items.order_id → orders"]

    key_findings(
        [
            f"**{len(catalog)} tables, {catalog['Rows'].sum() / 1e6:.2f}M rows.** Orders sit at the centre "
            f"(star-like model); geolocation alone is {geo.shape[0] / catalog['Rows'].sum():.0%} of all rows.",
            f"**orders → order_items is 1:N** - {(items_per_order > 1).mean():.1%} of orders have more than "
            f"one item (up to {int(item_fk['Max children per key'])}). Any order-level amount joined onto items "
            "gets repeated: this is the grain trap fixed in *Appendix → Cleaning & modeling*.",
            f"**`customer_id` is not a customer.** It is issued per order ({customers['customer_id'].nunique():,} ids) - "
            f"the real person is `customer_unique_id` ({customers['customer_unique_id'].nunique():,}). "
            "Repeat-purchase analysis must use the latter.",
            f"**Two keys that look unique are not:** {reviews['order_id'].duplicated().sum():,} orders have more than "
            f"one review, and geolocation has {len(geo) / geo['geolocation_zip_code_prefix'].nunique():.0f} GPS rows "
            "per zip prefix on average - both must be collapsed before joining.",
            f"**Keys are clean otherwise:** every order, product and seller key matches its parent (100%); only "
            f"{int(rels.loc['products.product_category_name → category_translation', 'Unmatched child rows'])} products "
            f"lack a category translation and {int(rels.loc['customers.customer_zip_code_prefix → geolocation', 'Unmatched child rows'])} "
            "customers lack coordinates.",
        ],
        so_what="Aggregate to a declared grain before every join, and pick the right customer key - "
        "otherwise revenue and retention numbers are silently wrong.",
    )
