import pandas as pd
import streamlit as st

from src.data_loader import load_item_level
from src.kpis import KPI_BY_KEY, monthly_kpis, period_slice, reporting_periods, scorecard
from src.metrics import REPEAT_WINDOW_DAYS, late_vs_on_time, repeat_by_category
from src.story import QUESTIONS, question_label
from src.theme import section_header

MIN_STATE_ORDERS = 300
# (background, accent) per priority - red = act now, amber = next, blue = test and learn.
PRIORITY_STYLE = {
    "High": ("#FDECEC", "#B42318"),
    "Medium": ("#FFF6DD", "#B07A00"),
    "Low": ("#EAF2FB", "#1F5A99"),
}


@st.cache_data
def recommendations() -> list:
    """Each action with the evidence behind it and a rough, stated-assumption impact."""
    card = scorecard()
    periods = reporting_periods()
    cur = period_slice("current")
    monthly = monthly_kpis().set_index("month")
    lvo = late_vs_on_time()
    neg_uplift = lvo.loc["Late", "negative_share"] - lvo.loc["On time / early", "negative_share"]
    late_target = KPI_BY_KEY["late"].target
    months_in_period = cur["month"].nunique()

    # 1. Peak-season readiness: Black Friday 2018 at 2018 volume with 2017's peak late rate.
    peak_month = monthly["orders"].idxmax()
    peak = monthly.loc[peak_month]
    pre_peak = monthly.loc[peak_month - pd.DateOffset(months=2):peak_month - pd.DateOffset(months=1), "orders"].mean()
    cur_avg = monthly.loc[periods["current"][0]:periods["current"][1], "orders"].mean()
    peak_2018 = peak["orders"] * cur_avg / pre_peak
    avoided_peak = peak_2018 * (peak["late"] - late_target)
    crisis = monthly[(monthly["late"] > 2 * late_target) & (monthly.index != peak_month)]

    # 2. Regional logistics: bring the worst states down to the national late rate.
    delivered = cur[(cur["order_status"] == "delivered") & cur["delivery_days"].notna()]
    national = delivered["is_late"].mean()
    states = delivered.groupby("customer_state").agg(orders=("order_id", "size"), late=("is_late", "mean"))
    worst = states[states["orders"] >= MIN_STATE_ORDERS].nlargest(5, "late")
    avoided_regional = ((worst["late"] - national) * worst["orders"]).sum() * 12 / months_in_period
    # Outside the peak months, to show the regional gap is structural rather than seasonal.
    off_peak = delivered[~delivered["month"].isin(crisis.index.union([peak_month]))]
    off_peak_states = off_peak[off_peak["customer_state"].isin(worst.index)]["is_late"].mean()
    off_peak_national = off_peak["is_late"].mean()

    # 3. Retention: who actually comes back, by first-purchase category.
    by_cat, overall_repeat = repeat_by_category()
    best = by_cat.head(3)
    category = load_item_level().groupby("order_id")["product_category_name_english"].first()
    new_buyers = cur[(cur["order_seq"] == 1) & (cur["order_status"] != "canceled")]
    new_buyers = new_buyers["order_id"].map(category).value_counts().reindex(best.index).fillna(0)
    # Doubling the repeat rate adds as many returning customers as return today.
    extra_returning = (new_buyers * best["repeat"]).sum() * 12 / months_in_period

    return [
        dict(
            priority="High", owner="Logistics & Operations",
            title=f"Add peak-season capacity for Black Friday {periods['as_of'].year}",
            evidence=(f"Late rate jumped to {peak['late']:.0%} in {peak_month:%b %Y} (Black Friday) and went above "
                      f"{2 * late_target:.0%} again in {', '.join(f'{m:%b %Y}' for m in crisis.index)}. Those months drove "
                      f"the YoY rise in late deliveries ({card.loc['late', 'prior']:.1%} → {card.loc['late', 'current']:.1%})."),
            action=(f"Short-term, all regions, Nov–Dec only: book extra carrier and seller-dispatch capacity for "
                    f"~{peak_2018:,.0f} orders in the peak month, add buffer days to promised dates while volume is "
                    "high, and track the late rate weekly from 1 Nov."),
            impact=(f"At ~{peak_2018:,.0f} orders expected in the peak month, holding the late rate at "
                    f"{late_target:.0%} instead of {peak['late']:.0%} avoids ~{avoided_peak:,.0f} late orders and "
                    f"~{avoided_peak * neg_uplift:,.0f} negative reviews."),
            kpi="Late delivery rate, negative reviews",
        ),
        dict(
            priority="Medium", owner="Logistics & Operations",
            title="Fix year-round delivery to the worst-served states",
            evidence=(f"{', '.join(worst.index)} run at {worst['late'].min():.0%}–{worst['late'].max():.0%} late vs. "
                      f"{national:.1%} nationally in {periods['label']}; most sellers ship from the south-east."),
            action=(f"Long-term, structural: {', '.join(worst.index)} run {off_peak_states:.0%} late even outside peak "
                    f"months (vs. {off_peak_national:.0%} nationally) because most sellers ship from the south-east. "
                    "Bring supply closer: open a regional fulfilment hub or recruit local sellers in these states."),
            impact=(f"Bringing these 5 states to the national rate avoids ~{avoided_regional:,.0f} late orders and "
                    f"~{avoided_regional * neg_uplift:,.0f} negative reviews per year."),
            kpi="Late delivery rate by state",
        ),
        dict(
            priority="Low", owner="CRM & Marketing",
            title="Pilot a second-purchase program in repeat-friendly categories",
            evidence=(f"Only {overall_repeat:.0%} of first-time buyers order again within {REPEAT_WINDOW_DAYS} days - "
                      "even after an on-time, 5-star experience. Repeat is highest in "
                      f"{', '.join(f'{c} ({v:.0%})' for c, v in best['repeat'].items())}."),
            action=(f"Test a second-order voucher with first-time buyers in {', '.join(best.index)} - the categories "
                    "where customers already return most - against a control group before any wider rollout."),
            impact=(f"Shows whether retention can be moved at all; doubling repeat in these categories would add "
                    f"~{extra_returning:,.0f} returning customers per year."),
            kpi="Orders from returning customers",
        ),
    ]


def _style_boxes() -> None:
    css = "".join(
        f".st-key-rec-{p.lower()} {{background:{bg}; border-left:6px solid {accent}; border-radius:8px; "
        f"padding:16px 20px;}}"
        for p, (bg, accent) in PRIORITY_STYLE.items()
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def render() -> None:
    section_header(f"{question_label(3)} · {QUESTIONS[3]}")
    _style_boxes()
    for r in recommendations():
        accent = PRIORITY_STYLE[r["priority"]][1]
        with st.container(key=f"rec-{r['priority'].lower()}"):
            st.markdown(
                f'<span style="color:{accent};font-weight:700;letter-spacing:.04em">{r["priority"].upper()} PRIORITY</span>',
                unsafe_allow_html=True,
            )
            st.markdown(f"#### {r['title']}")
            st.markdown(r["action"].replace("$", "\\$"))
