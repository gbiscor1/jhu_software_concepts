Architecture
============

Layers
------

- Web: Flask routes/templates. Renders pages and triggers actions.
- Application: Orchestrates pipelines (pull data, update analysis).
- Data: DB connection, loader (upsert), query runner (saved SQL).

Data Flow
---------

1. Pull Data → scrape/clean/(optional LLM) → upsert into ``applicants``.
2. Update Analysis → run ``src/sql/queries/q*.sql`` → write ``src/app/data/q*.json``.
3. UI reads JSON cards and renders big-number or table.
