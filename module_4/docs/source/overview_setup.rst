Overview & Setup
================


Prerequisites
-------------
- Python 3.11+
- PostgreSQL (local or container)
- Environment variable: ``DATABASE_URL`` (PostgreSQL DSN)


Local environment (PowerShell)
------------------------------
.. code-block:: powershell


# create and activate a virtual environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1


# install dependencies
pip install -r requirements.txt


# set required environment (persist in .env or current shell)
$env:DATABASE_URL = "postgresql://user:pass@localhost:5432/gradcafe"
$env:FLASK_ENV = "development"


Run the application
-------------------
.. code-block:: powershell


# from module_4
set FLASK_APP=src/run.py
py -m flask run
# open http://127.0.0.1:5000


Run the test suite
------------------
.. code-block:: powershell


# full suite with required markers and 100% coverage gate
pytest -m "web or buttons or analysis or db or integration"


# see detailed coverage
pytest --cov=src --cov-report=term-missing -q


Project layout (excerpt)
------------------------
::


module_4/
docs/
source/
conf.py
index.rst
overview_setup.rst
architecture.rst
testing_guide.rst
operational_notes.rst
troubleshooting.rst
api/
index.rst
requirements.txt