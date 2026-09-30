"""Metadata for the Olist relational model: tables, keys, and relationships."""

import pandas as pd
import streamlit as st

from src.data_loader import RAW_FILES, DATA_DIR, load_raw
from src.theme import BRAND_COLOR, INK, NEUTRAL_GREY

# role: "fact" = one row per business event, "dim" = descriptive attributes,
# "lookup" = reference / mapping data.
TABLES = {
    "orders": dict(role="fact", pk=["order_id"], grain="1 row per order", desc="Order header: status and lifecycle timestamps"),
    "order_items": dict(role="fact", pk=["order_id", "order_item_id"], grain="1 row per item in an order", desc="Product, seller, price and freight per item"),
    "order_payments": dict(role="fact", pk=["order_id", "payment_sequential"], grain="1 row per payment", desc="Payment method, installments and amount"),
    "order_reviews": dict(role="fact", pk=["review_id", "order_id"], grain="1 row per review", desc="1-5 star score and optional comment"),
    "customers": dict(role="dim", pk=["customer_id"], grain="1 row per order's customer", desc="Customer location; customer_unique_id identifies the person"),
    "sellers": dict(role="dim", pk=["seller_id"], grain="1 row per seller", desc="Seller location"),
    "products": dict(role="dim", pk=["product_id"], grain="1 row per product", desc="Category (Portuguese), size and weight"),
    "category_translation": dict(role="lookup", pk=["product_category_name"], grain="1 row per category", desc="Portuguese -> English category name"),
    "geolocation": dict(role="lookup", pk=[], grain="Many rows per zip prefix", desc="Lat/lng samples per zip code prefix"),
}

# (child table, child column, parent table, parent column, designed cardinality)
RELATIONSHIPS = [
    ("orders", "customer_id", "customers", "customer_id", "1:1"),
    ("order_items", "order_id", "orders", "order_id", "N:1"),
    ("order_items", "product_id", "products", "product_id", "N:1"),
    ("order_items", "seller_id", "sellers", "seller_id", "N:1"),
    ("order_payments", "order_id", "orders", "order_id", "N:1"),
    ("order_reviews", "order_id", "orders", "order_id", "N:1"),
    ("products", "product_category_name", "category_translation", "product_category_name", "N:1"),
    ("customers", "customer_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix", "N:M"),
    ("sellers", "seller_zip_code_prefix", "geolocation", "geolocation_zip_code_prefix", "N:M"),
]

_ROLE_COLOR = {"fact": BRAND_COLOR, "dim": "#7ED9A8", "lookup": "#E5E5E5"}


@st.cache_data
def table_catalog() -> pd.DataFrame:
    rows = []
    for name, meta in TABLES.items():
        df = load_raw(name)
        pk_dupes = int(df.duplicated(subset=meta["pk"]).sum()) if meta["pk"] else None
        rows.append(
            {
                "Table": name,
                "Role": meta["role"],
                "Rows": len(df),
                "Columns": df.shape[1],
                "Size (MB)": round((DATA_DIR / RAW_FILES[name]).stat().st_size / 1e6, 1),
                "Primary key": ", ".join(meta["pk"]) or "(none)",
                "PK duplicates": pk_dupes,
                "Grain": meta["grain"],
                "Description": meta["desc"],
            }
        )
    return pd.DataFrame(rows)


@st.cache_data
def relationship_stats() -> pd.DataFrame:
    """Measure each foreign key against its parent: match rate of the child's
    keys, how many parent rows have at least one child, and max fan-out."""
    rows = []
    for child, ccol, parent, pcol, card in RELATIONSHIPS:
        c = load_raw(child)[[ccol]].dropna()
        p = load_raw(parent)[[pcol]].drop_duplicates()
        joined = c.merge(p, left_on=ccol, right_on=pcol, how="left", indicator=True)
        parent_keys = load_raw(parent)[pcol].dropna().unique()
        child_counts = c[ccol].value_counts()
        rows.append(
            {
                "Child → Parent": f"{child}.{ccol} → {parent}",
                "Cardinality": card,
                "Child rows": len(c),
                "Unmatched child rows": int((joined["_merge"] == "left_only").sum()),
                "Match rate": (joined["_merge"] == "both").mean(),
                "Parents with ≥1 child": pd.Index(parent_keys).isin(child_counts.index).mean(),
                "Max children per key": int(child_counts.max()),
            }
        )
    return pd.DataFrame(rows)


def _node(name: str) -> str:
    meta = TABLES[name]
    cols = load_raw(name).columns
    fks = {ccol for child, ccol, *_ in RELATIONSHIPS if child == name}
    lines = []
    for col in cols:
        tag = "PK " if col in meta["pk"] else ("FK " if col in fks else "")
        if tag:
            lines.append(f'<tr><td align="left"><b>{tag}</b>{col}</td></tr>')
    other = len(cols) - len(lines)
    if other:
        lines.append(f'<tr><td align="left"><font color="{NEUTRAL_GREY}">+ {other} more columns</font></td></tr>')
    header = f'<tr><td bgcolor="{_ROLE_COLOR[meta["role"]]}"><b>{name}</b><br/>{meta["role"]} · {len(load_raw(name)):,} rows</td></tr>'
    return f'"{name}" [label=<<table border="0" cellborder="1" cellspacing="0" cellpadding="4">{header}{"".join(lines)}</table>>];'


def build_dot() -> str:
    """Graphviz DOT source for the ER diagram (rendered by st.graphviz_chart)."""
    nodes = "\n".join(_node(name) for name in TABLES)
    # Crow's foot notation: the "many" end of each relationship gets the crow.
    ends = {"1:1": ("tee", "tee"), "N:1": ("crow", "tee"), "N:M": ("crow", "crow")}
    edges = "\n".join(
        f'"{child}" -> "{parent}" [label=" {card} ", arrowtail={ends[card][0]}, arrowhead={ends[card][1]}];'
        for child, _, parent, _, card in RELATIONSHIPS
    )
    return f"""digraph olist {{
        rankdir=LR; bgcolor="transparent";
        node [shape=plaintext, fontname="Helvetica", fontsize=11, fontcolor="{INK}"];
        edge [dir=both, color="{NEUTRAL_GREY}", fontname="Helvetica", fontsize=10, fontcolor="{INK}"];
        {nodes}
        {edges}
    }}"""
