Operational Notes
=================


Busy-state policy
-----------------
``/pull-data`` and ``/update-analysis`` respect a mutual exclusion lock to prevent concurrent runs. Busy requests return 409 and perform no action.


Idempotency & uniqueness
------------------------
- Upserts use a deterministic PID derived from URLs to prevent duplicate inserts.
- Re-running pulls with overlapping data does not create duplicates.


Database connectivity
---------------------
- ``data.psych_connect`` reads ``DATABASE_URL`` and provides context managers for connections and cursors.