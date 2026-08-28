# Olist Brazilian E-Commerce Dashboard

[![Live Demo](https://img.shields.io/badge/Live_Demo-brazilian--e--commerce--f4g54pnlecrcpe78uuhovp.streamlit.app-06C755?style=flat-square&logo=streamlit&logoColor=white)](https://brazilian-e-commerce-f4g54pnlecrcpe78uuhovp.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.9-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)
![Progress](https://img.shields.io/badge/Progress-deployed-brightgreen?style=flat-square)

An interactive Streamlit dashboard analyzing ~99K real orders from Olist, a Brazilian marketplace
(2016-2018). Joins 9 relational CSV files into one denormalized table and surfaces it across 5
tabs covering sales, delivery performance, reviews, and geographic revenue.

## Preview

---

| Overview | Sales Overview | Delivery Performance |
|:---:|:---:|:---:|
| ![Overview](docs/img/preview-overview.png) | ![Sales Overview](docs/img/preview-sales-overview.png) | ![Delivery Performance](docs/img/preview-delivery-performance.png) |

## Features

- 5-tab dashboard: Overview, Sales Overview, Delivery Performance, Reviews, Geo Map
- Data pipeline joining 9 CSVs (order, customer, item, payment, review, product, and geolocation
  data) into a cached, denormalized order-level table
- Fixed USD display conversion and a shared Plotly chart-styling system for a consistent look
- Deployed on Streamlit Community Cloud

## Project Structure

```
Brazilian E-Commerce/
├── app.py                    # Entry point: Overview + Sales/Delivery/Reviews/Geo Map tabs
├── src/
│   ├── data_loader.py        # Cached loaders for each CSV + the joined order-level table
│   ├── currency.py           # Fixed BRL→USD display conversion
│   └── theme.py           # Brand color palette + shared Plotly chart styling
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

- Built the join/ETL pipeline into a 113K-row denormalized table and fixed 4 data-integrity bugs
  along the way, including a silent date-parsing failure and a category-mapping gap that was
  dropping revenue from every category chart.
- Found that delivery delay tightens from -5.9 to -13.4 days as review scores rise from 1 to 5
  stars, using a diverging color scale to make the trend readable at a glance.
- Redesigned every chart against a systematic color methodology instead of default styling,
  catching a map silently centered on Africa and a Plotly title bug in the process.
- Migrated the UI from a multi-page app to a single-page tabbed layout and verified every release
  with headless-browser testing.
