from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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
    return df.merge(translation, on="product_category_name", how="left")


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
def load_orders_full() -> pd.DataFrame:
    """Orders joined with customers, items, payments, reviews, and products.

    This is the main denormalized table most dashboard pages should query.
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

    df["delivery_days"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["delay_days"] = (
        df["order_delivered_customer_date"] - df["order_estimated_delivery_date"]
    ).dt.days
    df["is_late"] = df["delay_days"] > 0
    return df
