import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import load_geolocation, load_orders_full

st.set_page_config(page_title="Geo Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Customer & Revenue Map")

df = load_orders_full()
geo = load_geolocation()

by_zip = (
    df.groupby("customer_zip_code_prefix", as_index=False)
    .agg(orders=("order_id", "nunique"), revenue=("payment_value", "sum"), state=("customer_state", "first"))
)
by_zip = by_zip.merge(
    geo, left_on="customer_zip_code_prefix", right_on="geolocation_zip_code_prefix", how="inner"
)

st.caption(f"{len(by_zip):,} zip-code points plotted (aggregated from {df['order_id'].nunique():,} orders).")

fig = px.scatter_map(
    by_zip,
    lat="geolocation_lat",
    lon="geolocation_lng",
    size="revenue",
    color="state",
    hover_name="customer_zip_code_prefix",
    hover_data={"orders": True, "revenue": ":,.0f", "geolocation_lat": False, "geolocation_lng": False},
    zoom=3,
    height=700,
    map_style="open-street-map",
)
st.plotly_chart(fig, width="stretch")
