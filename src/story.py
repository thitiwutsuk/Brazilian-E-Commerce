"""The report's storyline: the three questions it answers, and the peak months
where delivery broke down - shared so every tab tells the same story."""

import pandas as pd

from src.kpis import KPI_BY_KEY, monthly_kpis

QUESTIONS = {
    1: "Are we really growing, and where does the revenue come from?",
    2: "Is the customer experience keeping up with the growth?",
    3: "What should we do before Black Friday 2018?",
}


def question_label(*numbers: int) -> str:
    return " & ".join(f"Q{n}" for n in numbers)


def crisis_months() -> pd.DataFrame:
    """Months whose late-delivery rate was more than double the target."""
    m = monthly_kpis()
    return m[m["late"] > 2 * KPI_BY_KEY["late"].target]


def annotate_crises(fig, y_col: str = "late", yref: str = "y", scale: float = 100, below: bool = False) -> None:
    """Label each crisis month on a late-rate line: 'Nov 2017 · 12%'. `below` puts the label under the
    point, for charts where another line runs above it."""
    for _, row in crisis_months().iterrows():
        fig.add_annotation(
            x=row["month"], y=row[y_col] * scale, yref=yref,
            text=f"<b>{row['month']:%b %Y}</b><br>{row[y_col]:.0%} late",
            showarrow=True, arrowhead=0, ax=0, ay=48 if below else -36, font=dict(size=12),
            bgcolor="rgba(255,255,255,0.9)",
        )
