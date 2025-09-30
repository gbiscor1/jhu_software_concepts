-- Q1 — Count how many rows are for the Fall 2025 term
SELECT
  COUNT(*) AS fall_2025_count   -- count all rows that match the WHERE clause
FROM applicants
WHERE
  term ILIKE 'Fall 2025';       -- case-insensitive