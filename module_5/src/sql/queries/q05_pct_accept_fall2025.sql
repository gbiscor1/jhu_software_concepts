-- Q5 — Percentage of Fall 2025 entries accepted

SELECT
  ROUND(
    100.0
    * COUNT(*) FILTER (                 -- count accepted rows within Fall 2025
        WHERE status ILIKE 'Accept%'    -- accept / accepted / acceptance variants
      )::numeric
    / NULLIF(COUNT(*), 0),              -- divide by total Fall 2025 entries; avoid zero division
  2) AS pct_acceptances_fall_2025
FROM applicants
WHERE
  term ILIKE 'Fall 2025';               -- only consider the Fall 2025
