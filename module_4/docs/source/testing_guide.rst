Testing Guide
=============


Running tests
-------------
Use required markers to select subsuites:


.. code-block:: bash


pytest -m "web or buttons or analysis or db or integration"


Markers
-------
- ``web`` — route/page rendering
- ``buttons`` — pull/update behavior and busy gating
- ``analysis`` — labels and percentage formatting
- ``db`` — schema/inserts/selects and idempotency
- ``integration`` — end-to-end flows


Selectors
---------
- ``[data-testid="pull-data-btn"]``
- ``[data-testid="update-analysis-btn"]``
- ``[data-testid="answer-label"]``


Environment
-----------
- ``DATABASE_URL`` is required. Tests may override via environment or fixtures.


Coverage
--------
- The suite enforces 100% coverage via ``pytest.ini``. Generate HTML with ``pytest --cov=src --cov-report=html``.