Troubleshooting
===============

- ``psycopg.OperationalError`` on connect → verify ``DATABASE_URL`` and that PostgreSQL is running.
- 409 responses from POST routes → a previous ``pull-data`` is still in progress; retry after completion.
- Missing selectors in tests → ensure templates are up to date and using ``data-testid`` attributes.
- Import errors in Sphinx autodoc → confirm ``sys.path`` includes ``../../src`` in ``conf.py``.