"""Headline metrics shared by the report tabs and the executive summary, so a
number quoted in the summary is always computed exactly as in its own tab."""

import pandas as pd
import streamlit as st

from src.data_loader import load_item_level, load_order_level
from src.quality import analysis_window

LOW_SCORE = 2  # reviews at or below this are "negative"


@st.cache_data
def delivered_orders() -> pd.DataFrame:
    df = load_order_level()
    return df[(df["order_status"] == "delivered") & df["delivery_days"].notna()]


@st.cache_data
def late_vs_on_time() -> pd.DataFrame:
    """Review outcome for late vs. on-time delivered orders."""
    df = delivered_orders().dropna(subset=["review_score"])
    out = df.groupby("is_late").agg(
        orders=("order_id", "size"),
        avg_review=("review_score", "mean"),
        negative_share=("review_score", lambda s: (s <= LOW_SCORE).mean()),
    )
    return out.rename(index={False: "On time / early", True: "Late"})


@st.cache_data
def monthly_sales() -> pd.DataFrame:
    """Orders and revenue per month inside the analysis window, with MoM change."""
    start, end = analysis_window()
    df = load_order_level()
    df = df[df["month"].between(start, end) & (df["order_status"] != "canceled")]
    out = df.groupby("month").agg(orders=("order_id", "size"), revenue=("payment_value", "sum")).reset_index()
    out["orders_mom"] = out["orders"].pct_change()
    out["revenue_mom"] = out["revenue"].pct_change()
    return out


@st.cache_data
def yoy_growth() -> dict:
    """Year-over-year growth on the months both years have in full (Jan-Aug)."""
    m = monthly_sales()
    last_year = m["month"].dt.year.max()
    months = m.loc[m["month"].dt.year == last_year, "month"].dt.month
    same = m[m["month"].dt.month.isin(months)]
    by_year = same.groupby(same["month"].dt.year)[["orders", "revenue"]].sum()
    growth = by_year.loc[last_year] / by_year.loc[last_year - 1] - 1
    return dict(year=last_year, first_month=months.min(), last_month=months.max(),
                orders=growth["orders"], revenue=growth["revenue"])


@st.cache_data
def peak_day() -> pd.Series:
    orders = load_order_level()
    daily = orders.groupby(orders["order_purchase_timestamp"].dt.normalize()).size()
    return pd.Series({"date": daily.idxmax(), "orders": daily.max(), "median": daily.median()})


def pareto(df: pd.DataFrame, key: str, value: str = "revenue") -> pd.DataFrame:
    out = df.groupby(key, as_index=False)[value].sum().sort_values(value, ascending=False).reset_index(drop=True)
    out["share"] = out[value] / out[value].sum()
    out["cum_share"] = out["share"].cumsum()
    out["rank"] = out.index + 1
    return out


@st.cache_data
def category_pareto() -> pd.DataFrame:
    items = load_item_level()
    return pareto(items[items["order_status"] != "canceled"], "product_category_name_english")


@st.cache_data
def seller_pareto() -> pd.DataFrame:
    items = load_item_level()
    return pareto(items[items["order_status"] != "canceled"], "seller_id")


def n_for_share(p: pd.DataFrame, share: float = 0.8) -> int:
    """How many top entries it takes to reach `share` of the total."""
    return int((p["cum_share"] < share).sum() + 1)


@st.cache_data
def orders_per_customer() -> pd.Series:
    return load_order_level().groupby("customer_unique_id")["order_id"].nunique()
