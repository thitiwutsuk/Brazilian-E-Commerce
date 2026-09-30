import pandas as pd
import streamlit as st

from src.currency import fmt_money_short
from src.data_loader import load_item_level
from src.kpis import KPI_BY_KEY, fmt_target, monthly_kpis, period_slice, reporting_periods, scorecard
from src.metrics import late_vs_on_time
from src.story import QUESTIONS, question_label
from src.theme import section_header

MIN_STATE_ORDERS = 300
PRIORITY_COLOR = {"High": "#B42318", "Medium": "#8A6100", "Low": "#475467"}


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

    # 3. Retention: +1 pp of orders from returning customers.
    valid = cur[cur["order_status"] != "canceled"]
    annual_orders = len(valid) * 12 / months_in_period
    retention_gmv = annual_orders * 0.01 * valid["payment_value"].mean()

    # 4. Seller concentration.
    items = load_item_level()
    items = items[items["month"].between(*periods["current"]) & (items["order_status"] != "canceled")]
    sellers = items.groupby("seller_id")["revenue"].sum().sort_values(ascending=False)
    top_n = max(1, len(sellers) // 100)
    top_share = sellers.head(top_n).sum() / sellers.sum()

    return [
        dict(
            priority="High", owner="Logistics & Operations",
            title=f"Prepare delivery capacity for Black Friday {periods['as_of'].year}",
            evidence=(f"Late rate jumped to {peak['late']:.0%} in {peak_month:%b %Y} (Black Friday) and went above "
                      f"{2 * late_target:.0%} again in {', '.join(f'{m:%b %Y}' for m in crisis.index)}. Those months drove "
                      f"the YoY rise in late deliveries ({card.loc['late', 'prior']:.1%} → {card.loc['late', 'current']:.1%})."),
            action="Agree carrier capacity and seller dispatch SLAs for Nov–Dec now; add buffer days to delivery "
                   "promises during the peak; monitor late rate weekly from 1 Nov.",
            impact=(f"At ~{peak_2018:,.0f} orders expected in the peak month, holding the late rate at "
                    f"{late_target:.0%} instead of {peak['late']:.0%} avoids ~{avoided_peak:,.0f} late orders and "
                    f"~{avoided_peak * neg_uplift:,.0f} negative reviews."),
            kpi="Late delivery rate, negative reviews",
        ),
        dict(
            priority="High", owner="Logistics & Operations",
            title="Fix delivery to the worst-served states",
            evidence=(f"{', '.join(worst.index)} run at {worst['late'].min():.0%}–{worst['late'].max():.0%} late vs. "
                      f"{national:.1%} nationally in {periods['label']}; most sellers ship from the south-east."),
            action="Review carrier mix and estimated-date rules for these states; recruit sellers or a regional "
                   "hub closer to the north-east.",
            impact=(f"Bringing these 5 states to the national rate avoids ~{avoided_regional:,.0f} late orders and "
                    f"~{avoided_regional * neg_uplift:,.0f} negative reviews per year."),
            kpi="Late delivery rate by state",
        ),
        dict(
            priority="Medium", owner="CRM & Marketing",
            title="Launch a second-purchase program",
            evidence=(f"Only {card.loc['returning', 'current']:.1%} of orders come from returning customers "
                      f"(target {fmt_target(KPI_BY_KEY['returning'])}); growth relies on acquiring new buyers."),
            action="Post-delivery email/voucher for a second order within 60 days, targeted at customers who left "
                   "4-5 star reviews; A/B test before full rollout.",
            impact=f"Every +1 pp of orders from returning customers ≈ +{annual_orders * 0.01:,.0f} orders and "
                   f"+{fmt_money_short(retention_gmv)} GMV per year.",
            kpi="Orders from returning customers",
        ),
        dict(
            priority="Medium", owner="Seller Success",
            title="Protect the top sellers",
            evidence=f"The top 1% of sellers ({top_n} of {len(sellers):,}) generate {top_share:.0%} of item revenue "
                     f"in {periods['label']}.",
            action="Assign account managers to the top sellers; track their late rate and review score monthly "
                   "and act before they churn or degrade.",
            impact=f"Protects ~{fmt_money_short(sellers.head(top_n).sum() * 12 / months_in_period)} of annual item "
                   "revenue concentrated in a few accounts.",
            kpi="GMV share and late rate of top sellers",
        ),
        dict(
            priority="Low", owner="Data Intelligence",
            title="Adopt this scorecard as the monthly business review",
            evidence="Targets in this report are proposed by the analyst - there are no official ones yet.",
            action="Confirm targets with each KPI owner and review the scorecard monthly; add weekly late-rate "
                   "alerts during peak season.",
            impact="Problems like the Feb–Mar 2018 delivery crisis get caught within a week instead of a quarter.",
            kpi="All scorecard KPIs",
        ),
    ]


def render() -> None:
    section_header(
        f"{question_label(3)} · {QUESTIONS[3]} And what is each action worth?",
        "Each action is tied to a KPI that is off track. Impacts are rough estimates that assume the "
        "relationships observed in the data continue to hold - they size the opportunity, not a forecast.",
    )
    for i, r in enumerate(recommendations(), 1):
        with st.container(border=True):
            st.markdown(
                f'<span style="color:{PRIORITY_COLOR[r["priority"]]};font-weight:700">{r["priority"]} priority</span>'
                f' · Owner: {r["owner"]} · KPI: {r["kpi"]}',
                unsafe_allow_html=True,
            )
            st.markdown(f"#### {i}. {r['title']}")
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Why**\n\n{r['evidence']}".replace("$", "\\$"))
            col2.markdown(f"**Action**\n\n{r['action']}".replace("$", "\\$"))
            col3.markdown(f"**Estimated impact**\n\n{r['impact']}".replace("$", "\\$"))
