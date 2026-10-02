"""The report's storyline: the three questions it answers, and the peak months
where delivery broke down - shared so every tab tells the same story."""

import pandas as pd

from src.kpis import KPI_BY_KEY, monthly_kpis

QUESTIONS = {
    1: "เราโตจริงไหม และรายได้มาจากไหน?",
    2: "ประสบการณ์ลูกค้าตามการเติบโตทันไหม?",
    3: "ก่อน Black Friday 2018 เราควรทำอะไร?",
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
            text=f"<b>{row['month']:%b %Y}</b><br>ส่งช้า {row[y_col]:.0%}",
            showarrow=True, arrowhead=0, ax=0, ay=48 if below else -36, font=dict(size=12),
            bgcolor="rgba(255,255,255,0.9)",
        )


def highlight_crises(fig, label: str = "ส่งช้าและรีวิวแย่พุ่งพร้อมกัน") -> None:
    """Shade each run of consecutive crisis months so the eye lands on where both lines jump."""
    months = list(crisis_months()["month"])
    runs, start = [], None
    for i, m in enumerate(months):
        start = start or m
        if i == len(months) - 1 or months[i + 1] != m + pd.DateOffset(months=1):
            runs.append((start, m))
            start = None
    for i, (a, b) in enumerate(runs):
        fig.add_vrect(
            x0=a - pd.Timedelta(days=15), x1=b + pd.Timedelta(days=15),
            fillcolor="#E34948", opacity=0.10, line_width=0, layer="below",
            annotation_text=label if i == 0 else "", annotation_position="top left",
            annotation_font=dict(size=11, color="#B42318"),
        )
