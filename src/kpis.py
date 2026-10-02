"""KPI definitions, targets, and the reporting period used across the report.

The dataset carries no official targets. The targets below are set by the
analyst as a reasonable bar for a marketplace at this stage, and are shown in
the app as such.
"""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.data_loader import load_order_level
from src.quality import analysis_window

LOW_SCORE = 2  # reviews at or below this are "negative"


@dataclass(frozen=True)
class Kpi:
    key: str
    label: str
    fmt: str  # "money", "int", "pct", "score", "days"
    higher_is_better: bool
    target: float
    definition: str
    meaning: str  # why a manager should care


KPIS = [
    Kpi("gmv", "GMV", "money", True, 0.30, "Total paid by customers on non-canceled orders (payments incl. freight).",
        "Size of the business. Target is growth: ≥ +30% vs. the same period last year."),
    Kpi("orders", "Orders", "int", True, 0.30, "Non-canceled orders placed in the period.",
        "Demand volume. Target is growth: ≥ +30% vs. the same period last year."),
    Kpi("aov", "Avg. order value", "money", True, 0.0, "GMV ÷ orders.",
        "How much each order is worth. Target: no decline vs. last year."),
    Kpi("customers", "Active customers", "int", True, 0.30, "Distinct customers (customer_unique_id) with an order.",
        "Reach of the marketplace. Target: ≥ +30% vs. last year."),
    Kpi("returning", "Orders from returning customers", "pct", True, 0.05,
        "Share of orders placed by a customer who had ordered before.",
        "Loyalty. Low means growth depends on buying new customers."),
    Kpi("late", "Late delivery rate", "pct", False, 0.05,
        "Delivered orders that arrived after the date promised to the customer.",
        "Reliability of our delivery promise - the strongest driver of bad reviews."),
    Kpi("review", "Avg. review score", "score", True, 4.0, "Mean 1-5 star score of reviewed orders.",
        "Overall customer satisfaction."),
    Kpi("negative", "Negative reviews", "pct", False, 0.12, f"Share of reviews with 1-{LOW_SCORE} stars.",
        "Unhappy customers - they rarely come back and hurt seller ratings."),
    Kpi("delivery_days", "Avg. delivery time", "days", False, 12.0, "Days from purchase to delivery, delivered orders.",
        "Speed customers experience."),
    Kpi("cancel", "Cancellation rate", "pct", False, 0.01, "Orders with status canceled ÷ all orders.",
        "Lost sales and wasted acquisition spend."),
]
KPI_BY_KEY = {k.key: k for k in KPIS}
GROWTH_KPIS = {"gmv", "orders", "customers"}  # target is on YoY change, not the level
FLAT_KPIS = {"aov"}  # target is "no decline" YoY


@st.cache_data
def reporting_periods() -> dict:
    """Current = year-to-date of the latest full year in the analysis window;
    prior = the same calendar months one year earlier."""
    _, end = analysis_window()
    cur_start = pd.Timestamp(year=end.year, month=1, day=1)
    prior_start, prior_end = cur_start - pd.DateOffset(years=1), end - pd.DateOffset(years=1)
    return dict(
        current=(cur_start, end),
        prior=(prior_start, prior_end),
        label=f"Jan–{end:%b %Y}",
        prior_label=f"Jan–{prior_end:%b %Y}",
        as_of=end + pd.offsets.MonthEnd(0),
    )


def compute(df: pd.DataFrame) -> dict:
    """All KPI values for one slice of the order-level table."""
    valid = df[df["order_status"] != "canceled"]
    delivered = df[(df["order_status"] == "delivered") & df["delivery_days"].notna()]
    reviews = df["review_score"].dropna()
    return dict(
        gmv=valid["payment_value"].sum(),
        orders=len(valid),
        aov=valid["payment_value"].mean(),
        customers=valid["customer_unique_id"].nunique(),
        returning=(valid["order_seq"] > 1).mean(),
        late=delivered["is_late"].mean(),
        review=reviews.mean(),
        negative=(reviews <= LOW_SCORE).mean(),
        delivery_days=delivered["delivery_days"].mean(),
        cancel=(df["order_status"] == "canceled").mean(),
    )


def period_slice(name: str) -> pd.DataFrame:
    start, end = reporting_periods()[name]
    df = load_order_level()
    return df[df["month"].between(start, end)]


@st.cache_data
def scorecard() -> pd.DataFrame:
    """Current vs. prior period for every KPI, with status against target."""
    cur, prior = compute(period_slice("current")), compute(period_slice("prior"))
    rows = []
    for k in KPIS:
        change = cur[k.key] / prior[k.key] - 1
        rows.append(dict(key=k.key, current=cur[k.key], prior=prior[k.key], change=change,
                         status=status(k, cur[k.key], change)))
    return pd.DataFrame(rows).set_index("key")


def status(k: Kpi, value: float, change: float) -> str:
    """On track = meets target; Watch = misses by less than 10% of the target; else Off track."""
    measured = change if k.key in GROWTH_KPIS | FLAT_KPIS else value
    gap = (measured - k.target) if k.higher_is_better else (k.target - measured)
    if gap >= 0:
        return "On track"
    scale = abs(k.target) if k.target else 0.05
    return "Watch" if -gap <= 0.10 * scale else "Off track"


@st.cache_data
def monthly_kpis() -> pd.DataFrame:
    """Every KPI per month inside the analysis window."""
    start, end = analysis_window()
    df = load_order_level()
    df = df[df["month"].between(start, end)]
    return pd.DataFrame({m: compute(g) for m, g in df.groupby("month")}).T.rename_axis("month").reset_index()


def fmt_value(k: Kpi, v: float) -> str:
    from src.currency import fmt_money, fmt_money_short

    if k.fmt == "money":
        return fmt_money_short(v) if v >= 1e5 else fmt_money(v)
    if k.fmt == "int":
        return f"{v:,.0f}"
    if k.fmt == "pct":
        return f"{v:.1%}"
    if k.fmt == "score":
        return f"{v:.2f} / 5"
    return f"{v:.1f} days"


def fmt_target(k: Kpi) -> str:
    if k.key in GROWTH_KPIS:
        return f"≥ {k.target:+.0%} YoY"
    if k.key in FLAT_KPIS:
        return "no YoY decline"
    sign = "≥" if k.higher_is_better else "≤"
    return f"{sign} {fmt_value(k, k.target)}"


def fmt_delta(k: Kpi, cur: float, prior: float) -> str:
    """Rates move in percentage points, scores in points, everything else in %."""
    if k.fmt == "pct":
        return f"{(cur - prior) * 100:+.1f} pp YoY"
    if k.fmt == "score":
        return f"{cur - prior:+.2f} YoY"
    if k.fmt == "days":
        return f"{cur - prior:+.1f} days YoY"
    return f"{cur / prior - 1:+.0%} YoY"


def render_cards(keys: list, per_row: int = 4) -> None:
    """KPI cards: value, YoY change, status vs. target, and what it means."""
    from src.theme import kpi_card

    card = scorecard()
    for i in range(0, len(keys), per_row):
        for col, key in zip(st.columns(per_row), keys[i:i + per_row]):
            k, row = KPI_BY_KEY[key], card.loc[key]
            with col:
                kpi_card(
                    label=k.label,
                    value=fmt_value(k, row["current"]),
                    delta=fmt_delta(k, row["current"], row["prior"]),
                    higher_is_better=k.higher_is_better,
                    status=row["status"],
                    target=fmt_target(k),
                    meaning=k.meaning.split(" Target")[0],
                    help=f"{k.definition} Last year: {fmt_value(k, row['prior'])}.",
                )
