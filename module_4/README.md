# JHU EP 605.256 — Assignment 4: Pytest + Sphinx

**Student:** Gabriel Bisco Reinato

## Overview

Flask web app with PostgreSQL backend. Builds on Module 3 by adding full test coverage with `pytest` and publishable documentation with Sphinx. UI exposes two actions: **Pull Data** (scrape → clean → upsert) and **Update Analysis** (run saved SQL → write JSON cards).

## Requirements

* Python **3.10+**
* PostgreSQL
* `pip install -r module_4/requirements.txt`
* `.env` in `module_4/`:

  ```
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=gradcafe_db
  DB_USER=postgres
  DB_PASSWORD=postgres
  SECRET_KEY=<64+ hex chars>
  ```

Quickstart
----------

.. code-block:: bash

   # from repo root
   cd module_4
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt

   python src/scripts/init_db.py
   python src/run.py
   # open http://127.0.0.1:5000

## UI actions

* **Pull Data** — runs Module 2 pipeline (via adapter) and upserts into `applicants`.
* **Update Analysis** — executes `src/sql/queries/q*.sql` and writes `src/app/data/q*.json`.

## Documentation (Sphinx)

Build local HTML:

```bash
# from module_4/
sphinx-build -b html docs/source docs/build
# open module_4/docs/build/index.html
```

## Testing

Markers used: `web`, `buttons`, `analysis`, `db`, `integration`.

Run targeted suites:

```bash
# from module_4/
pytest -m web -q
pytest -m buttons -q
pytest -m analysis -q
pytest -m db -q
pytest -m integration -q
```

Run all + coverage:

```bash
pytest --maxfail=1 -q
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html  # opens htmlcov/index.html
```

## Project layout

```text
module_4/
├─ .gitignore
├─ README.md
├─ requirements.txt
├─ docs/
│  └─ source/
│     ├─ conf.py
│     ├─ index.rst
│     ├─ overview_setup.rst
│     ├─ architecture.rst
│     ├─ testing_guide.rst
│     ├─ operational_notes.rst
│     ├─ troubleshooting.rst
│     └─ api/
│        ├─ index.rst
│        ├─ app.rst
│        ├─ application.rst
│        ├─ data.rst
│        └─ scripts.rst
├─ src/
│  ├─ __init__.py
│  ├─ run.py
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ routes.py
│  │  ├─ templates/
│  │  │  ├─ index.html
│  │  │  └─ analysis.html
│  │  └─ static/
│  │     └─ css/
│  │        └─ styles.css
│  ├─ application/
│  │  ├─ __init__.py
│  │  ├─ scrapper_cli_caller.py
│  │  └─ services.py
│  ├─ data/
│  │  ├─ __init__.py
│  │  ├─ loader.py
│  │  ├─ psych_connect.py
│  │  └─ query_runner.py
│  ├─ scripts/
│  │  ├─ __init__.py
│  │  ├─ init_db.py
│  │  ├─ load_db.py
│  │  └─ ping_db.py
│  └─ sql/
│     ├─ __init__.py
│     ├─ schema/
│     │  └─ schema.sql
│     └─ queries/
│        ├─ q01_total.sql
│        ├─ q01_total.txt
│        ├─ ...
├─ tests/
│  ├─ __init__.py
│  ├─ conftest.py
│  ├─ application/
│  │  ├─ test_scrapper_cli_caller.py
│  │  └─ test_services.py
│  ├─ data/
│  │  └─ test_query_runner.py
│  ├─ scripts/
│  │  ├─ test_load_db.py
│  │  └─ test_reset_db.py
│  ├─ test_analysis_format.py
│  ├─ test_buttons.py
│  ├─ test_db_insert.py
│  ├─ test_flask_page.py
│  └─ test_integration_end_to_end.py
└─ (generated at runtime / optional to commit)
   ├─ docs/build/                  # Sphinx HTML
   ├─ htmlcov/                     # coverage HTML
   └─ src/app/data/*.json          # analysis cards written by the app
```

## Queries (examples)

* `q01_*` — total applicants (scalar)
* `q02_*` — % international (two-decimal string)
* `q03_*` — averages (returns table)

Additional course-specific `q*.sql` files under `src/sql/queries/`.

## Documentation contents

* **Overview & Setup** — environment, run steps, test commands.
* **Architecture** — app layers (Web / Application / Data) and data flow.
* **API Reference** — autodoc pages for `app`, `application`, `data`, `scripts`.
* **Testing Guide** — markers, fixtures, selectors (`data-testid`), coverage notes.
* **Operational Notes** — busy-state lock, idempotent loader, connection settings.
* **Troubleshooting** — missing DSN, autodoc import path, build warnings.

## Acknowledgments and tooling disclosure

The following assets were initially generated with GPT and then reviewed and edited:

* Module and function **docstrings** (Sphinx-style).
* First versions of **test files** under `tests/`.
* First versions of **Sphinx `.rst`** pages under `docs/source/`.

Subsequent edits ensured assignment alignment, consistent tone, and passing tests.

## Submission checklist

* [ ] `docs/build/` present and opens `index.html` (or RTD URL added below).
* [ ] All tests pass; coverage report captured.
* [ ] `.env` excluded from VCS; `.gitignore` updated.
* [ ] README includes test instructions and documentation steps.

## Documentation

- Local HTML: [docs/build/index.html](./module_4/docs/build/index.html)
- Read the Docs: https://jhu-software-concepts-module-4.readthedocs.io/en/latest/

## References

* GradCafe — [https://www.thegradcafe.com](https://www.thegradcafe.com)
* RealPython -[https://realpython.com/pytest-python-testing/](https://realpython.com/pytest-python-testing/)
* Dockslikecode - [https://www.docslikecode.com/learn/01-sphinx-python-rtd/](https://www.docslikecode.com/learn/01-sphinx-python-rtd/)