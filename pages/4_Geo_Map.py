import pandas as pd
import plotly.express as px
import streamlit as st

from src.currency import currency_selector
from src.data_loader import load_geolocation, load_orders_full
from src.theme import SEQUENTIAL_GREEN, configure_page, style_fig

configure_page("Geo Map", "🗺️")
st.title("🗺️ Customer & Revenue Map")

symbol, rate = currency_selector()
df = load_orders_full()
geo = load_geolocation()

by_zip = (
    df.groupby("customer_zip_code_prefix", as_index=False)
    .agg(orders=("order_id", "nunique"), revenue=("payment_value", "sum"), state=("customer_state", "first"))
)
by_zip["revenue"] = by_zip["revenue"] / rate
by_zip = by_zip.merge(
    geo, left_on="customer_zip_code_prefix", right_on="geolocation_zip_code_prefix", how="inner"
)

# A handful of zip prefixes in the raw geolocation file are mis-geocoded outside
# Brazil entirely (e.g. one lands in Portugal, lat/lon ~41,-8.6). Only 3 zip
# prefixes / 4 orders are affected, but left in they force the map to zoom out
# to fit a stray point on another continent. Drop anything outside Brazil's
# real bounding box before plotting.
BRAZIL_BOUNDS = dict(lat_min=-34, lat_max=5.5, lon_min=-74, lon_max=-34)
in_brazil = by_zip["geolocation_lat"].between(BRAZIL_BOUNDS["lat_min"], BRAZIL_BOUNDS["lat_max"]) & by_zip[
    "geolocation_lng"
].between(BRAZIL_BOUNDS["lon_min"], BRAZIL_BOUNDS["lon_max"])
dropped = len(by_zip) - in_brazil.sum()
by_zip = by_zip[in_brazil]

st.caption(
    f"{len(by_zip):,} zip-code points plotted (aggregated from {df['order_id'].nunique():,} orders"
    f"{f', {dropped} mis-geocoded zip prefixes excluded' if dropped else ''}). "
    "Bubble size = order volume, color = revenue concentration — bigger + darker areas are both "
    "high-volume and high-value; bigger + lighter areas order a lot but at lower ticket sizes."
)

fig = px.scatter_map(
    by_zip,
    lat="geolocation_lat",
    lon="geolocation_lng",
    size="orders",
    color="revenue",
    color_continuous_scale=SEQUENTIAL_GREEN,
    # Revenue-per-zip is heavily right-skewed (median R$649 vs. max R$109,760 -
    # a single dense SP zip). A linear scale to the max would render everything
    # outside that handful of zips as near-white. Cap the color domain at the
    # 95th percentile so the color channel actually differentiates the bulk of
    # the map; the richest few zips just saturate at the darkest step.
    range_color=[0, by_zip["revenue"].quantile(0.95)],
    hover_name="customer_zip_code_prefix",
    hover_data={"state": True, "orders": True, "revenue": ":,.0f", "geolocation_lat": False, "geolocation_lng": False},
    labels={"revenue": f"Revenue ({symbol})", "orders": "Orders"},
    center={"lat": -14.2, "lon": -51.9},
    zoom=3.2,
    height=700,
    map_style="open-street-map",
)
fig.update_layout(coloraxis_colorbar_title=f"Revenue ({symbol})")
st.plotly_chart(style_fig(fig), width="stretch")
