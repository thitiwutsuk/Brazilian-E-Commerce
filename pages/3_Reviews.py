import plotly.express as px
import streamlit as st

from src.data_loader import load_order_reviews, load_orders_full

st.set_page_config(page_title="Reviews", page_icon="⭐", layout="wide")
st.title("⭐ Customer Reviews")

df = load_orders_full()
reviews = load_order_reviews()

col1, col2 = st.columns(2)
with col1:
    score_counts = df["review_score"].value_counts().sort_index().reset_index()
    score_counts.columns = ["review_score", "count"]
    st.plotly_chart(
        px.bar(score_counts, x="review_score", y="count", title="Review score distribution"),
        width="stretch",
    )
with col2:
    by_category = (
        df.dropna(subset=["review_score", "product_category_name_english"])
        .groupby("product_category_name_english", as_index=False)["review_score"]
        .mean()
        .merge(df["product_category_name_english"].value_counts().rename("n"), left_on="product_category_name_english", right_index=True)
    )
    by_category = by_category[by_category["n"] >= 30].sort_values("review_score").head(15)
    st.plotly_chart(
        px.bar(
            by_category,
            x="review_score",
            y="product_category_name_english",
            orientation="h",
            title="Lowest-rated categories (min. 30 orders)",
        ).update_layout(yaxis={"categoryorder": "total ascending"}),
        width="stretch",
    )

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
