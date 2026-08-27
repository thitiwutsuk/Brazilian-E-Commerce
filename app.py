import plotly.express as px
import streamlit as st

from src.currency import get_currency
from src.data_loader import load_geolocation, load_orders_full
from src.theme import ACCENT_RED, BRAND_COLOR, NEUTRAL_GREY, SCORE_COLOR, SCORE_SCALE, SEQUENTIAL_GREEN, configure_page, style_fig

configure_page("Olist E-Commerce Dashboard")
st.title("Brazilian E-Commerce (Olist) Dashboard")

GREEN = BRAND_COLOR
RED = ACCENT_RED

symbol, rate = get_currency()
df = load_orders_full()


def fmt(value: float) -> str:
    return f"{symbol}{value:,.0f}"


tab_overview, tab_sales, tab_delivery, tab_reviews, tab_geo = st.tabs(
    ["Overview", "Sales Overview", "Delivery Performance", "Reviews", "Geo Map"]
)

# ---------------------------------------------------------------- Overview
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Orders", f"{df['order_id'].nunique():,}")
    col2.metric("Customers", f"{df['customer_unique_id'].nunique():,}")
    col3.metric(f"Revenue ({symbol})", fmt(df["payment_value"].sum() / rate))
    col4.metric("Avg. review score", f"{df['review_score'].mean():.2f}")

    st.divider()
    st.subheader("Sample orders")
    st.caption("Random sample of 10 orders - not the full dataset.")

    sample_cols = {
        "order_purchase_timestamp": "Order date",
        "customer_state": "State",
        "product_category_name_english": "Category",
        "payment_value": f"Payment ({symbol})",
        "review_score": "Review score",
        "delivery_days": "Delivery (days)",
    }
    sample = (
        df.dropna(subset=["product_category_name_english", "delivery_days", "review_score"])
        .sample(10, random_state=42)[list(sample_cols)]
        .rename(columns=sample_cols)
        .sort_values("Order date")
    )
    sample[f"Payment ({symbol})"] = sample[f"Payment ({symbol})"] / rate
    st.dataframe(
        sample,
        width="stretch",
        hide_index=True,
        column_config={
            "Order date": st.column_config.DatetimeColumn(format="D MMM YYYY"),
            f"Payment ({symbol})": st.column_config.NumberColumn(format=f"{symbol}%.0f"),
            "Review score": st.column_config.NumberColumn(format="%.0f / 5"),
            "Delivery (days)": st.column_config.NumberColumn(format="%.0f d"),
        },
    )

# ------------------------------------------------------------ Sales Overview
with tab_sales:
    delivered = df[df["order_status"] == "delivered"].copy()
    delivered["revenue"] = delivered["payment_value"] / rate

    by_month = (
        delivered.assign(month=delivered["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)["revenue"]
        .sum()
    )
    peak = by_month.loc[by_month["revenue"].idxmax()]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total revenue", fmt(delivered["revenue"].sum()))
    col2.metric("Peak month", peak["month"].strftime("%b %Y"), fmt(peak["revenue"]))
    col3.metric("Avg. order value", fmt(delivered.groupby("order_id")["revenue"].sum().mean()))

    fig_month = px.line(
        by_month,
        x="month",
        y="revenue",
        title="Revenue by month",
        labels={"revenue": f"Revenue ({symbol})", "month": ""},
        markers=True,
    )
    fig_month.update_traces(line_color=GREEN, marker_color=GREEN)
    fig_month.add_scatter(
        x=[peak["month"]],
        y=[peak["revenue"]],
        mode="markers+text",
        text=[f"peak: {peak['month'].strftime('%b %Y')}"],
        textposition="top center",
        marker=dict(size=10, color=GREEN),
        showlegend=False,
    )
    st.plotly_chart(style_fig(fig_month), width="stretch")

    col1, col2 = st.columns(2)

    by_category = (
        delivered.groupby("product_category_name_english", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
        .head(5)
    )
    with col1:
        fig_cat = px.bar(
            by_category,
            x="revenue",
            y="product_category_name_english",
            orientation="h",
            title="Top 5 categories by revenue",
            labels={"revenue": f"Revenue ({symbol})", "product_category_name_english": ""},
            text=by_category["revenue"].map(fmt),
        )
        fig_cat.update_traces(marker_color=GREEN, textposition="outside")
        fig_cat.update_layout(
            yaxis={"categoryorder": "total ascending", "automargin": True},
            xaxis_range=[0, by_category["revenue"].max() * 1.2],
        )
        st.plotly_chart(style_fig(fig_cat), width="stretch")

    by_state = (
        delivered.groupby("customer_state", as_index=False)["revenue"]
        .sum()
        .sort_values("revenue", ascending=False)
        .head(5)
    )
    by_state["label"] = by_state["revenue"].map(fmt)
    with col2:
        fig_state = px.bar(
            by_state,
            x="customer_state",
            y="revenue",
            title="Revenue by customer state (top 5)",
            labels={"revenue": f"Revenue ({symbol})", "customer_state": ""},
            text="label",
        )
        fig_state.update_traces(marker_color=GREEN, textposition="outside")
        st.plotly_chart(style_fig(fig_state), width="stretch")

# --------------------------------------------------------- Delivery Performance
with tab_delivery:
    delivery_delivered = df[df["order_status"] == "delivered"].dropna(subset=["delivery_days", "delay_days"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg. delivery time (days)", f"{delivery_delivered['delivery_days'].mean():.1f}")
    col2.metric("Late deliveries", f"{delivery_delivered['is_late'].mean() * 100:.1f}%")
    col3.metric(
        "Avg. delay when late (days)",
        f"{delivery_delivered.loc[delivery_delivered['is_late'], 'delay_days'].mean():.1f}",
    )

    col1, col2 = st.columns(2)
    with col1:
        mean_days = delivery_delivered["delivery_days"].mean()
        fig_hist = px.histogram(
            delivery_delivered,
            x="delivery_days",
            nbins=40,
            title="Distribution of delivery time (days)",
            labels={"delivery_days": "Delivery time (days)"},
        )
        fig_hist.update_traces(marker_color=GREEN)
        fig_hist.add_vline(
            x=mean_days,
            line_color=NEUTRAL_GREY,
            annotation_text=f"mean: {mean_days:.1f} days",
            annotation_position="top",
        )
        # 99% of deliveries land under ~45 days; without capping the range, the ~1%
        # tail stretching to 209 days squeezes the entire meaningful distribution
        # into a sliver on the left.
        p99 = delivery_delivered["delivery_days"].quantile(0.99)
        fig_hist.update_xaxes(range=[0, p99])
        st.plotly_chart(style_fig(fig_hist), width="stretch")
    with col2:
        by_state_late = (
            delivery_delivered.groupby("customer_state", as_index=False)["is_late"]
            .mean()
            .sort_values("is_late", ascending=False)
            .head(5)
        )
        by_state_late["pct"] = by_state_late["is_late"] * 100
        by_state_late["label"] = by_state_late["pct"].map(lambda v: f"{v:.0f}%")
        fig_late = px.bar(
            by_state_late,
            x="customer_state",
            y="pct",
            title="Late delivery rate by customer state (worst 5)",
            labels={"pct": "Late deliveries (%)", "customer_state": ""},
            text="label",
        )
        fig_late.update_traces(marker_color=GREEN, textposition="outside")
        st.plotly_chart(style_fig(fig_late), width="stretch")

    st.caption("Top 10 states by order volume - the late-rate bar above shows how often orders are late; this shows how wide the actual delivery-time spread is.")
    top10_states = (
        delivery_delivered.groupby("customer_state")["delivery_days"].count().sort_values(ascending=False).head(10).index
    )
    box_df = delivery_delivered[delivery_delivered["customer_state"].isin(top10_states)]
    box_p99 = box_df["delivery_days"].quantile(0.99)
    fig_box = px.box(
        box_df,
        x="customer_state",
        y="delivery_days",
        title="Delivery time spread by state (top 10 by order volume)",
        labels={"customer_state": "", "delivery_days": "Delivery time (days)"},
        category_orders={"customer_state": list(top10_states)},
    )
    fig_box.update_traces(marker_color=GREEN, line_color=GREEN)
    fig_box.update_yaxes(range=[0, box_p99])
    st.plotly_chart(style_fig(fig_box), width="stretch")

    st.subheader("Delivery delay vs. review score")
    st.caption(
        "Delay is measured against the estimated delivery date - negative means the order "
        "arrived earlier than promised. Every score arrives early on average, but the "
        "gap widens sharply for higher scores: earlier delivery tracks with happier customers."
    )
    by_score_delay = delivery_delivered.groupby("review_score", as_index=False)["delay_days"].mean()
    by_score_delay["color"] = by_score_delay["delay_days"].apply(lambda v: RED if v > 0 else GREEN)
    fig_score = px.bar(
        by_score_delay,
        x="review_score",
        y="delay_days",
        title="Avg. delivery delay by review score (negative = early)",
        labels={"delay_days": "Avg. delay (days)", "review_score": "Review score"},
        text=by_score_delay["delay_days"].map(lambda v: f"{v:+.1f}d"),
    )
    fig_score.update_traces(marker_color=by_score_delay["color"], textposition="outside")
    fig_score.add_hline(y=0, line_color=NEUTRAL_GREY)
    st.plotly_chart(style_fig(fig_score), width="stretch")

# ---------------------------------------------------------------- Reviews
with tab_reviews:
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg. review score", f"{df['review_score'].mean():.2f} / 5")
    col2.metric("5-star share", f"{(df['review_score'] == 5).mean() * 100:.1f}%")
    col3.metric("1-star share", f"{(df['review_score'] == 1).mean() * 100:.1f}%")

    col1, col2 = st.columns(2)
    with col1:
        score_counts = df["review_score"].value_counts().sort_index().reset_index()
        score_counts.columns = ["review_score", "count"]
        fig_dist = px.bar(
            score_counts,
            x="review_score",
            y="count",
            title="Review score distribution",
            labels={"review_score": "Review score", "count": "Orders"},
            text=score_counts["count"].map(lambda v: f"{v:,}"),
        )
        fig_dist.update_traces(
            marker_color=[SCORE_COLOR[s] for s in score_counts["review_score"]],
            textposition="outside",
        )
        st.plotly_chart(style_fig(fig_dist), width="stretch")
    with col2:
        by_category_score = (
            df.dropna(subset=["review_score", "product_category_name_english"])
            .groupby("product_category_name_english", as_index=False)["review_score"]
            .mean()
            .merge(
                df["product_category_name_english"].value_counts().rename("n"),
                left_on="product_category_name_english",
                right_index=True,
            )
        )
        by_category_score = by_category_score[by_category_score["n"] >= 30].sort_values("review_score").head(5)
        fig_cat_score = px.bar(
            by_category_score,
            x="review_score",
            y="product_category_name_english",
            orientation="h",
            title="Lowest-rated categories (min. 30 orders)",
            labels={"review_score": "Avg. review score", "product_category_name_english": ""},
            color="review_score",
            color_continuous_scale=SCORE_SCALE,
            range_color=[1, 5],
            text=by_category_score["review_score"].map(lambda v: f"{v:.2f}"),
        )
        fig_cat_score.update_traces(textposition="outside")
        fig_cat_score.update_layout(
            yaxis={"categoryorder": "total ascending", "automargin": True},
            coloraxis_showscale=False,
            # Zoom to the data's actual range (all scores cluster ~3.2-3.9) instead of
            # 0-5 - on a 0-5 axis every bar looks the same length and the ranking is
            # invisible, which defeats the point of a "lowest-rated" chart.
            xaxis_range=[by_category_score["review_score"].min() - 0.2, by_category_score["review_score"].max() + 0.2],
        )
        st.plotly_chart(style_fig(fig_cat_score), width="stretch")

# ---------------------------------------------------------------- Geo Map
with tab_geo:
    geo = load_geolocation()

    by_zip = df.groupby("customer_zip_code_prefix", as_index=False).agg(
        orders=("order_id", "nunique"), revenue=("payment_value", "sum"), state=("customer_state", "first")
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

    fig_geo = px.scatter_map(
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
    fig_geo.update_layout(coloraxis_colorbar_title=f"Revenue ({symbol})")
    st.plotly_chart(style_fig(fig_geo), width="stretch")
