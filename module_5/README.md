### JHU EP 605.256 — Assignment 5: Software Assurance

Student: Gabriel Bisco Reinato

Overview

Flask web app with PostgreSQL backend, focused on software assurance: static analysis with pylint, dependency mapping with pydeps, supply-chain scanning with Snyk, and comprehensive tests with pytest + coverage.

## Requirements

Python 3.10+

PostgreSQL (only needed to run the app end-to-end)

pip install -r module_5/requirements.txt

.env in module_5/ (only for running the app):

DB_HOST=localhost
DB_PORT=5432
DB_NAME=gradcafe_db
DB_USER=postgres
DB_PASSWORD=postgres
SECRET_KEY=<64+ hex chars>


Generate a key:

python -c "import secrets; print(secrets.token_hex(32))"

## Quickstart

.. code-block:: bash

from repo root

cd module_5
python -m venv .venv
..venv\Scripts\Activate.ps1
pip install -r requirements.txt

## Linting (pylint)
# from module_5/
pylint --rcfile=.pylintrc --recursive=y -j 0 src tests

## Dependency graphs (pydeps)
# from module_5/
$env:PYTHONPATH = "$PWD"

# whole app graph
python -m pydeps src -T svg -o dependency.svg --noshow `
  --pylib --pylib-all --max-bacon 2 --cluster --rmprefix src. `
  --only src.app,src.application,src.data,src.sql

# focused graphs
python -m pydeps src/app/__init__.py -T svg -o src_app___init__.svg --noshow
python -m pydeps src/run.py          -T svg -o src_run.svg         --noshow

Snyk scan
# from module_5/
npm install -g snyk
snyk auth
snyk test --file=requirements.txt --package-manager=pip --skip-unresolved

## Testing
# from module_5/
pytest -q
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html  # open htmlcov/index.html

## Run app
# from module_5/
python src/scripts/init_db.py
python src/run.py
open http://127.0.0.1:5000

Project layout
module_5/
├─ .gitignore
├─ .pylintrc
├─ README.md
├─ requirements.txt
├─ src/
│  ├─ __init__.py
│  ├─ run.py
│  ├─ app/
│  │  ├─ __init__.py
│  │  ├─ routes.py
│  │  ├─ templates/
│  │  │  ├─ index.html
│  │  │  └─ analysis.html
│  │  └─ static/css/styles.css
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
│  │  └─ reset_db.py
│  └─ sql/
│     ├─ __init__.py
│     ├─ schema/schema.sql
│     └─ queries/
│        ├─ q01_total.sql
│        ├─ q01_total.txt
│        └─ ...
├─ tests/
│  ├─ __init__.py
│  ├─ conftest.py
│  ├─ application/test_services.py
│  ├─ data/test_query_runner.py
│  ├─ scripts/test_reset_db.py
│  ├─ test_analysis_format.py
│  ├─ test_buttons.py
│  ├─ test_db_insert.py
│  ├─ test_flask_page.py
│  └─ test_integration_end_to_end.py
└─ (generated)
   ├─ htmlcov/
   ├─ src/app/data/*.json
   ├─ dependency.svg
   ├─ src_app___init__.svg
   └─ src_run.svg

## References

Pylint — https://pylint.readthedocs.io/

pydeps — https://github.com/thebjorn/pydeps

Snyk — https://docs.snyk.io/

## Acknowledgments Disclosure

Some prose and small refactors were drafted with AI assistance (ChatGPT) and then reviewed and edited by me. All final code/configuration were validated locally.