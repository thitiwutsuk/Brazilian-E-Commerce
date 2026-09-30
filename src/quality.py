"""Data quality checks, payment reconciliation, and the cleansing log."""

import pandas as pd
import streamlit as st

from src.data_loader import (
    load_geolocation,
    load_order_level,
    load_orders_full,
    load_raw,
    load_reviews_latest,
)

# A month counts as "fully covered" when it has at least this many orders.
# The dataset's edges (late 2016, Sep-Oct 2018) have a handful of orders each
# and would read as fake crashes / spikes on any trend chart.
MIN_ORDERS_PER_MONTH = 500

# Reconciliation: payments vs. items (price + freight) per order.
RECON_ABS_TOLERANCE = 1.0  # BRL - rounding noise
RECON_ORDER_TOLERANCE = 0.01  # max share of orders allowed outside tolerance

BRAZIL_BOUNDS = dict(lat_min=-34, lat_max=5.5, lon_min=-74, lon_max=-34)


def _check(dimension, check, count, total, tolerance, action):
    rate = count / total if total else 0
    status = "PASS" if count == 0 else ("WARN" if rate <= tolerance else "FAIL")
    return dict(Dimension=dimension, Check=check, Status=status, Count=int(count), Rate=rate, Action=action)


@st.cache_data
def monthly_coverage() -> pd.DataFrame:
    """Orders per calendar month over a full date spine, so gap months show as 0."""
    orders = load_order_level()
    counts = orders.groupby("month").size()
    spine = pd.date_range(counts.index.min(), counts.index.max(), freq="MS")
    out = counts.reindex(spine, fill_value=0).rename_axis("month").reset_index(name="orders")
    out["in_window"] = out["orders"] >= MIN_ORDERS_PER_MONTH
    return out


def analysis_window() -> tuple:
    """First and last month of the longest run of fully covered months."""
    cov = monthly_coverage()
    run_id = (cov["in_window"] != cov["in_window"].shift()).cumsum()
    runs = cov[cov["in_window"]].groupby(run_id[cov["in_window"]])["month"]
    longest = max(runs, key=lambda kv: len(kv[1]))[1]
    return longest.min(), longest.max()


@st.cache_data
def reconcile_payments() -> pd.DataFrame:
    """Per order: what the customer paid vs. what the items + freight cost."""
    items = load_raw("order_items").assign(item_total=lambda d: d["price"] + d["freight_value"])
    items = items.groupby("order_id")["item_total"].sum()
    paid = load_raw("order_payments").groupby("order_id")["payment_value"].sum()
    df = pd.concat([paid, items], axis=1, join="inner").reset_index()
    df["diff"] = df["payment_value"] - df["item_total"]
    df["within_tolerance"] = df["diff"].abs() <= RECON_ABS_TOLERANCE
    return df


@st.cache_data
def run_checks() -> pd.DataFrame:
    orders = load_raw("orders")
    items = load_raw("order_items")
    payments = load_raw("order_payments")
    reviews = load_raw("order_reviews")
    customers = load_raw("customers")
    sellers = load_raw("sellers")
    products = load_raw("products")
    translation = load_raw("category_translation")
    geo = load_raw("geolocation")

    delivered_ts = pd.to_datetime(orders["order_delivered_customer_date"])
    purchase_ts = pd.to_datetime(orders["order_purchase_timestamp"])
    is_delivered = orders["order_status"] == "delivered"
    geo_zips = set(geo["geolocation_zip_code_prefix"])
    categorized = products["product_category_name"].dropna()
    cov = monthly_coverage()
    recon = reconcile_payments()

    checks = [
        # Uniqueness
        _check("Uniqueness", "orders.order_id is unique", orders["order_id"].duplicated().sum(), len(orders), 0,
               "-"),
        _check("Uniqueness", "products.product_id is unique", products["product_id"].duplicated().sum(), len(products), 0,
               "-"),
        _check("Uniqueness", "One review per order", reviews["order_id"].duplicated().sum(), len(reviews), 0.01,
               "Keep the most recently answered review per order"),
        # Completeness
        _check("Completeness", "Delivered orders have a delivery date", (is_delivered & delivered_ts.isna()).sum(),
               is_delivered.sum(), 0.01, "Excluded from delivery-time analysis"),
        _check("Completeness", "Products have a category", products["product_category_name"].isna().sum(),
               len(products), 0.02, "Labelled '(unknown)' so revenue is not dropped"),
        _check("Completeness", "Orders have a payment", (~orders["order_id"].isin(payments["order_id"])).sum(),
               len(orders), 0.01, "Kept; payment amount left empty"),
        _check("Completeness", "No gap months in the order timeline", (cov["orders"] == 0).sum(), len(cov), 0,
               f"Trend charts limited to months with ≥{MIN_ORDERS_PER_MONTH:,} orders"),
        # Referential integrity
        _check("Referential integrity", "Every order has at least one item",
               (~orders["order_id"].isin(items["order_id"])).sum(), len(orders), 0.01,
               "Mostly unavailable / canceled orders - kept with 0 items"),
        _check("Referential integrity", "Every category has an English translation",
               (~categorized.isin(translation["product_category_name"])).sum(), len(categorized), 0.01,
               "Fall back to the Portuguese name"),
        _check("Referential integrity", "Customer zip prefixes exist in geolocation",
               (~customers["customer_zip_code_prefix"].isin(geo_zips)).sum(), len(customers), 0.01,
               "Kept; location coordinates unavailable"),
        _check("Referential integrity", "Seller zip prefixes exist in geolocation",
               (~sellers["seller_zip_code_prefix"].isin(geo_zips)).sum(), len(sellers), 0.01,
               "Kept; location coordinates unavailable"),
        # Validity
        _check("Validity", "Item price > 0", (items["price"] <= 0).sum(), len(items), 0, "-"),
        _check("Validity", "Payment value > 0", (payments["payment_value"] <= 0).sum(), len(payments), 0.001,
               "Voucher-only payments - kept"),
        _check("Validity", "Review score within 1-5", (~reviews["review_score"].between(1, 5)).sum(), len(reviews), 0,
               "-"),
        _check("Validity", "Delivered on/after purchase", (delivered_ts < purchase_ts).sum(), len(orders), 0, "-"),
        _check("Validity", "Geolocation inside Brazil",
               (~geo["geolocation_lat"].between(BRAZIL_BOUNDS["lat_min"], BRAZIL_BOUNDS["lat_max"])
                | ~geo["geolocation_lng"].between(BRAZIL_BOUNDS["lon_min"], BRAZIL_BOUNDS["lon_max"])).sum(),
               len(geo), 0.001, "Excluded from location data"),
        # Accuracy
        _check("Accuracy", f"Paid = items + freight (±R${RECON_ABS_TOLERANCE:.0f})", (~recon["within_tolerance"]).sum(),
               len(recon), RECON_ORDER_TOLERANCE, "Accepted - mostly installment interest"),
    ]
    return pd.DataFrame(checks)


@st.cache_data
def cleansing_log() -> pd.DataFrame:
    """Row counts before/after every preparation step, in pipeline order."""
    raw_reviews = load_raw("order_reviews")
    raw_payments = load_raw("order_payments")
    raw_items = load_raw("order_items")
    raw_geo = load_raw("geolocation")
    geo = load_geolocation()
    in_brazil = geo["geolocation_lat"].between(BRAZIL_BOUNDS["lat_min"], BRAZIL_BOUNDS["lat_max"]) & geo[
        "geolocation_lng"
    ].between(BRAZIL_BOUNDS["lon_min"], BRAZIL_BOUNDS["lon_max"])
    orders = load_order_level()
    delivered = orders[(orders["order_status"] == "delivered") & orders["delivery_days"].notna()]
    start, end = analysis_window()

    steps = [
        ("Reviews", "Deduplicate to one review per order (latest answer)", len(raw_reviews), len(load_reviews_latest())),
        ("Payments", "Aggregate split payments to order level", len(raw_payments), raw_payments["order_id"].nunique()),
        ("Items", "Aggregate items to order level for the order fact", len(raw_items), raw_items["order_id"].nunique()),
        ("Order fact", "Left-join orders ← customers, items, payments, reviews", len(load_raw("orders")), len(orders)),
        ("Delivery subset", "Keep delivered orders with a delivery date", len(orders), len(delivered)),
        ("Trend subset", f"Keep {start:%b %Y} – {end:%b %Y} (months ≥{MIN_ORDERS_PER_MONTH} orders)", len(orders),
         int(orders["month"].between(start, end).sum())),
        ("Geolocation", "Collapse GPS samples to one median point per zip prefix", len(raw_geo), len(geo)),
        ("Geolocation", "Drop points outside Brazil's bounding box", len(geo), int(in_brazil.sum())),
    ]
    df = pd.DataFrame(steps, columns=["Table", "Step", "Rows before", "Rows after"])
    df["Change"] = df["Rows after"] - df["Rows before"]
    return df


@st.cache_data
def grain_comparison() -> pd.DataFrame:
    """Revenue under the naive item-level join vs. the correct grains."""
    naive = load_orders_full()
    orders = load_order_level()
    items = load_raw("order_items")
    rows = [
        ("Naive join (payment_value on every item row)", "1 row per item", len(naive), naive["payment_value"].sum()),
        ("Order fact (payments summed per order)", "1 row per order", len(orders), orders["payment_value"].sum()),
        ("Item fact (price + freight per item)", "1 row per item", len(items), (items["price"] + items["freight_value"]).sum()),
    ]
    df = pd.DataFrame(rows, columns=["Table", "Grain", "Rows", "Revenue (BRL)"])
    df["vs. order fact"] = df["Revenue (BRL)"] / df.loc[1, "Revenue (BRL)"] - 1
    return df
