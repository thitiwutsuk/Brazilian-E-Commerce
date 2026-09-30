# Olist Brazilian E-Commerce Dashboard

[![Live Demo](https://img.shields.io/badge/Live_Demo-brazilian--e--commerce--f4g54pnlecrcpe78uuhovp.streamlit.app-06C755?style=flat-square&logo=streamlit&logoColor=white)](https://brazilian-e-commerce-f4g54pnlecrcpe78uuhovp.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.9-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Progress](https://img.shields.io/badge/Progress-deployed-brightgreen?style=flat-square)

A management business review built in Streamlit, written as the Olist Data Intelligence team
reporting to the Head of Marketplace. It covers ~99K real orders (2016-2018) and compares
Jan–Aug 2018 with the same months of 2017: a KPI scorecard with targets, the story behind the
numbers, and recommended actions with sized impact.

## Preview

---

| Executive Summary | Appendix | Customer Experience |
|:---:|:---:|:---:|
| ![Executive Summary](docs/img/preview-summary.png) | ![Data Architecture](docs/img/preview-architecture.png) | ![Customer Experience](docs/img/preview-experience.png) |

## Features

- Executive Summary: bottom line, KPI scorecard (YoY change + On track / Watch / Off track vs.
  target), what went well / what needs attention, top actions
- Sales & Growth, Customer Experience, Customers & Markets: KPI cards, charts with a plain-language
  "what this means", and key findings
- Recommendations: 5 actions with owner, priority, evidence and estimated impact
- Appendix: KPI definitions; data architecture (data flow from raw CSVs to report, raw
  data explorer, ER diagram, table catalog, foreign-key checks); 17 automated data quality checks,
  payment reconciliation and the cleansing log
- Two fact tables with an explicit grain: order-level (1 row per order) and item-level
  (1 row per order item)
- Fixed USD display conversion and a shared Plotly chart-styling system for a consistent look
- Deployed on Streamlit Community Cloud

## Project Structure

```
Brazilian E-Commerce/
├── app.py                    # Entry point: builds the report tabs
├── src/
│   ├── data_loader.py        # Cached loaders for each CSV + order-level and item-level fact tables
│   ├── schema.py             # Table/key metadata, FK match rates, ER diagram (Graphviz DOT)
│   ├── quality.py            # Data quality checks, reconciliation, cleansing log
│   ├── kpis.py               # KPI definitions, targets, reporting period, scorecard
│   ├── metrics.py            # Shared metrics used by the tabs and the summary
│   ├── sections/             # One module per report tab
│   ├── currency.py           # Fixed BRL→USD display conversion
│   └── theme.py              # Brand color palette, Plotly styling, findings box
├── data/                     # Raw Olist CSVs
├── docs/                     # Reusable Streamlit theming notes
├── .streamlit/config.toml    # Theme
└── requirements.txt          # Python dependencies, version-pinned
```

## Dataset

Olist Store public e-commerce dataset. 9 CSV files (~99K orders, 1M+ geolocation records) joined
via `order_id`, `customer_id`, `product_id`, `seller_id`, and zip code prefix.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Engineering Highlights

- Found that joining order-level payments onto order items inflated revenue by 28%. Rebuilt the
  model as two fact tables with an explicit grain, with an assertion that the order table
  cannot fan out.
- Reconciled payments against items + freight: totals differ by 0.02%, and only 0.25% of orders
  are off by more than R$1.
- Showed that late orders are 6.7x as likely to get a 1-2 star review (62% vs. 9%), and traced
  the YoY doubling of the late rate (3.5% → 7.7%) to three peak months, starting with Black
  Friday 2017.
- Redesigned every chart against a systematic color methodology instead of default styling,
  catching a map silently centered on Africa and a Plotly title bug in the process.
- Migrated the UI from a multi-page app to a single-page tabbed layout and verified every release
  with headless-browser testing.
