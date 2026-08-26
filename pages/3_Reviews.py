import plotly.express as px
import streamlit as st

from src.data_loader import load_order_reviews, load_orders_full

st.set_page_config(page_title="Reviews", page_icon="⭐", layout="wide")
st.title("⭐ Customer Reviews")

RED = "#e34948"
NEUTRAL = "#898781"
BLUE = "#2a78d6"
DIVERGING_SCALE = [RED, NEUTRAL, BLUE]
SCORE_COLOR = {1: "#e34948", 2: "#c46f68", 3: NEUTRAL, 4: "#5a80ac", 5: BLUE}

df = load_orders_full()
reviews = load_order_reviews()

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
    st.plotly_chart(fig_dist, width="stretch")
with col2:
    by_category = (
        df.dropna(subset=["review_score", "product_category_name_english"])
        .groupby("product_category_name_english", as_index=False)["review_score"]
        .mean()
        .merge(df["product_category_name_english"].value_counts().rename("n"), left_on="product_category_name_english", right_index=True)
    )
    by_category = by_category[by_category["n"] >= 30].sort_values("review_score").head(15)
    fig_cat = px.bar(
        by_category,
        x="review_score",
        y="product_category_name_english",
        orientation="h",
        title="Lowest-rated categories (min. 30 orders)",
        labels={"review_score": "Avg. review score", "product_category_name_english": ""},
        color="review_score",
        color_continuous_scale=DIVERGING_SCALE,
        range_color=[1, 5],
        color_continuous_midpoint=3,
        text=by_category["review_score"].map(lambda v: f"{v:.2f}"),
    )
    fig_cat.update_traces(textposition="outside")
    fig_cat.update_layout(
        yaxis={"categoryorder": "total ascending", "automargin": True},
        coloraxis_showscale=False,
        # Zoom to the data's actual range (all scores cluster ~3.2-3.9) instead of
        # 0-5 - on a 0-5 axis every bar looks the same length and the ranking is
        # invisible, which defeats the point of a "lowest-rated" chart.
        xaxis_range=[by_category["review_score"].min() - 0.2, by_category["review_score"].max() + 0.2],
    )
    st.plotly_chart(fig_cat, width="stretch")

st.subheader("Sample of written reviews")
with_text = reviews.dropna(subset=["review_comment_message"])
score_filter = st.multiselect("Filter by score", options=sorted(reviews["review_score"].unique()), default=[])
if score_filter:
    with_text = with_text[with_text["review_score"].isin(score_filter)]
st.dataframe(
    with_text[["review_score", "review_comment_title", "review_comment_message"]].sample(
        min(50, len(with_text)), random_state=42
    ),
    width="stretch",
)
