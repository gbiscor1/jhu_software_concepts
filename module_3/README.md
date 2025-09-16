# JHU EP 605.256 — Assignment 3: GradCafe Analytics Web App

**Student:** Gabriel Bisco Reinato

## Overview

A small Flask web app that answers analytics questions over GradCafe results stored in PostgreSQL. It reuses Module 2 (scrape/clean/optional LLM) and adds:

* A single applicants table in Postgres
* Buttons to **Pull Data** (upsert fresh results) and **Update Analysis** (run queries)
* Server-rendered “cards” that read precomputed JSON from `module_3/app/data/`

## Requirements

* Python **3.10+**
* PostgreSQL
* `pip install -r module_3/requirements.txt`
* A `.env` in `module_3/`:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gradcafe_db
DB_USER=postgres
DB_PASSWORD=postgres
```

## Quickstart

```powershell
# from repo root
cd module_3
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# initialize DB and bulk-load 20k rows
python .\scripts\reset_db.py --bulk .\data\database_bulk.json

# run the web app
python .\run.py
# open http://127.0.0.1:5000
```

**In the UI**

* **Pull Data** - runs Module 2 pipeline and upserts rows from 
* **Update Analysis** - executes every query in `sql/queries/q*.sql` and updates the main page.

## Queries

* `q01_fall_2025_count.sql` — count of Fall 2025 applicants
* `q02_percentage_international.sql` — % international (2 decimals)
* `q03_metric_averages.sql` — avg GPA/GRE/GRE-V/GRE-AW
* `q04_avg_gpa_amer_fall2025.sql` — avg GPA for American Fall 2025 applicants
* `q05_pct_accept_fall2025.sql` — % accepted among Fall 2025
* `q06_avg_gpa_fall2025_accepts.sql` — avg GPA of accepted Fall 2025 applicants
* `q07_count_jhu_ms_cs.sql` — JHU MS CS count
* `q08_count_2025_georgetown_phd_cs_accept.sql` — 2025 Georgetown CS PhD accepts
* `q09_jhu_ai_vs_cs_ms_this_year.sql` — JHU YTD admits, AI vs CS
* `q10_jhu_gpa_major_comparison.sql` — JHU GPA: Engineering vs Medicine vs Other


## Project Tree (abridged)

```
jhu_sc/
├─ module_2/
│  ├─ app.py, scrape.py, clean.py
│  ├─ data/
│  │  ├─ applicant_data.json    # 20,000 scrapped rows
│  │  ├─ applicant_data.cleaned.json    # 20,000 cleaned rows
│  │  └─ llm_extend_applicant_data.json # 20,000 llm normalized rows
│  └─ llm_hosting/app.py    # LLM entry point
└─ module_3/
   ├─ .env, requirements.txt, run.py
   ├─ app/
   │  ├─ __init__.py
   │  ├─ routes.py                            # loads app/data/*.json and routes to the application layer
   │  ├─ data/                                # queries and answers in json format
   │  └─ ...
   │  ├─ static/styles.css                    # Style for all html files
   │  └─ templates/
   │     ├─ grid_template.html, card_template.html
   │     ├─ query_page.html                   # grid of cards
   │     └─ query_card.html                   # encapsulation of queries for display
   ├─ application/
   │  ├─ scrapper_cli_caller.py               # call module_2 via cli
   │  └─ services.py                          # contorller between front and data layers
   ├─ data/
   │  ├─ psych_connect.py                     # psycopg connector
   │  ├─ loader.py                            # inserts applicants into table (if not duplicate)
   │  └─ query_runner.py                      # runs sql queries and saves the outputs in json
   ├─ scripts/
   │  ├─ reset_db.py                          # reset the data table with the bulk json data
   │  └─ ping_db.py / init_db.py (utils)      # ping for debugging and initialization of the db table
   └─ sql/
      ├─ schema/schema.sql
      └─ queries/
         ├─ qXX_*.sql                         # sql queries
         └─ qXX_*.txt                         # txt queries for display
```

## Acknowledgments

The following artifacts were initially generated with GPT and then reviewed, edited, and integrated by me:
-All SQL query files under module_3/sql/queries/q*.sql
-All HTML templates in module_3/app/templates/
-Stylesheet at module_3/app/static/styles.css
-All test files
-Project .gitignore

Improvements suggested by the LLM that I adopted and adapted:
-Environment & secrets: use a .env file loaded in code (via python-dotenv), ship a .env.example, keep .env out of version control, and document setup in the README.
-Scraper orchestration (application/scrapper_cli_caller.py): run the scraper without LLM first, then do a single LLM pass after cleaning to improve reliability and avoid crashy multi-pass behavior.
-Most messages flowing from application and data layer to frontend for debugging

## References

* [https://www.thegradcafe.com](https://www.thegradcafe.com)
