from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}

# Zip prefixes have leading zeros ("01310") - reading them as int would break
# joins against any table that kept them as text.
ZIP_DTYPES = {
    "customer_zip_code_prefix": str,
    "seller_zip_code_prefix": str,
    "geolocation_zip_code_prefix": str,
}


@st.cache_data
def load_raw(name: str) -> pd.DataFrame:
    """A source CSV exactly as shipped - used for profiling and quality checks."""
    return pd.read_csv(DATA_DIR / RAW_FILES[name], dtype=ZIP_DTYPES)


@st.cache_data
def load_orders() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    date_cols = [c for c in df.columns if c.endswith(("_date", "_at", "_timestamp"))]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col])
    return df


@st.cache_data
def load_order_items() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "olist_order_items_dataset.csv")
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"])
    return df


@st.cache_data
def load_order_payments() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")


@st.cache_data
def load_order_reviews() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "olist_order_reviews_dataset.csv")
    for col in ("review_creation_date", "review_answer_timestamp"):
        df[col] = pd.to_datetime(df[col])
    return df


@st.cache_data
def load_customers() -> pd.DataFrame:
    return pd.read_csv(
        DATA_DIR / "olist_customers_dataset.csv",
        dtype={"customer_zip_code_prefix": str},
    )


@st.cache_data
def load_sellers() -> pd.DataFrame:
    return pd.read_csv(
        DATA_DIR / "olist_sellers_dataset.csv",
        dtype={"seller_zip_code_prefix": str},
    )


@st.cache_data
def load_products() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "olist_products_dataset.csv")
    translation = pd.read_csv(DATA_DIR / "product_category_name_translation.csv")
    df = df.merge(translation, on="product_category_name", how="left")
    # A few category names (e.g. "pc_gamer") have no row in the translation file.
    # Without this, those products' revenue silently disappears from any chart
    # that groups by the English column (pandas groupby drops NaN keys).
    df["product_category_name_english"] = df["product_category_name_english"].fillna(
        df["product_category_name"]
    )
    return df


@st.cache_data
def load_geolocation() -> pd.DataFrame:
    df = pd.read_csv(
        DATA_DIR / "olist_geolocation_dataset.csv",
        dtype={"geolocation_zip_code_prefix": str},
    )
    # One zip prefix can have many lat/lng rows (GPS noise); collapse to a
    # single representative point so joins don't fan out order/customer rows.
    return df.groupby("geolocation_zip_code_prefix", as_index=False).agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_city=("geolocation_city", "first"),
        geolocation_state=("geolocation_state", "first"),
    )


@st.cache_data
def load_reviews_latest() -> pd.DataFrame:
    """One review per order: when an order was reviewed more than once, keep the
    most recently answered review as the customer's final verdict."""
    return (
        load_order_reviews()
        .sort_values("review_answer_timestamp")
        .drop_duplicates("order_id", keep="last")[["order_id", "review_score"]]
    )


def _add_delivery_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df["delivery_days"] = (df["order_delivered_customer_date"] - df["order_purchase_timestamp"]).dt.days
    df["delay_days"] = (df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]).dt.days
    df["is_late"] = df["delay_days"] > 0
    return df


@st.cache_data
def load_order_level() -> pd.DataFrame:
    """Order-level fact table. Grain: one row per order_id.

    Items and payments are aggregated to the order *before* joining, so no
    order-level amount is ever repeated across rows.
    """
    orders = load_orders()
    items = load_order_items().groupby("order_id", as_index=False).agg(
        n_items=("order_item_id", "count"),
        n_sellers=("seller_id", "nunique"),
        item_price=("price", "sum"),
        freight_value=("freight_value", "sum"),
    )
    payments = load_order_payments()
    main_type = (
        payments.sort_values("payment_value", ascending=False)
        .drop_duplicates("order_id")[["order_id", "payment_type"]]
    )
    payments = (
        payments.groupby("order_id", as_index=False)
        .agg(payment_value=("payment_value", "sum"), payment_installments=("payment_installments", "max"))
        .merge(main_type, on="order_id")
    )

    df = (
        orders.merge(load_customers(), on="customer_id", how="left")
        .merge(items, on="order_id", how="left")
        .merge(payments, on="order_id", how="left")
        .merge(load_reviews_latest(), on="order_id", how="left")
    )
    assert len(df) == len(orders) and df["order_id"].is_unique, "order-level join fanned out"
    df["n_items"] = df["n_items"].fillna(0).astype(int)
    df["month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    # 1 = the customer's first order ever, 2 = their second, ...
    df["order_seq"] = (
        df.sort_values("order_purchase_timestamp").groupby("customer_unique_id").cumcount().reindex(df.index) + 1
    )
    return _add_delivery_metrics(df)


@st.cache_data
def load_item_level() -> pd.DataFrame:
    """Item-level fact table. Grain: one row per (order_id, order_item_id).

    Revenue here is the item's own price + freight, so it can be summed by
    product category or seller without double counting.
    """
    orders = load_orders()[["order_id", "customer_id", "order_status", "order_purchase_timestamp"]]
    df = (
        load_order_items()
        .merge(orders, on="order_id", how="left")
        .merge(load_customers()[["customer_id", "customer_state"]], on="customer_id", how="left")
        .merge(load_products()[["product_id", "product_category_name_english"]], on="product_id", how="left")
    )
    df["product_category_name_english"] = df["product_category_name_english"].fillna("(unknown)")
    df["revenue"] = df["price"] + df["freight_value"]
    df["month"] = df["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    return df


@st.cache_data
def load_orders_full() -> pd.DataFrame:
    """Naive join of every table onto order items (kept for comparison only).

    Grain is one row per order item, but order-level columns such as
    payment_value repeat on every item row - summing them over-counts revenue.
    Use load_order_level() / load_item_level() for analysis.
    """
    orders = load_orders()
    customers = load_customers()
    items = load_order_items()
    payments = (
        load_order_payments()
        .groupby("order_id", as_index=False)
        .agg(payment_value=("payment_value", "sum"), payment_installments=("payment_installments", "max"))
    )
    reviews = load_order_reviews()[["order_id", "review_score"]].drop_duplicates("order_id")
    products = load_products()

    df = orders.merge(customers, on="customer_id", how="left")
    df = df.merge(items, on="order_id", how="left")
    df = df.merge(products, on="product_id", how="left")
    df = df.merge(payments, on="order_id", how="left")
    df = df.merge(reviews, on="order_id", how="left")
    return _add_delivery_metrics(df)
