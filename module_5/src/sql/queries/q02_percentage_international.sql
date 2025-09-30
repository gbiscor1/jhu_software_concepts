-- Q2 — The percentage of entries that are "international"

SELECT
  ROUND(                         -- format to 2 decimal places
    100.0                        -- convert fraction to percentage
    * COUNT(*) FILTER (          -- count only the rows that meet condition
        WHERE us_or_international IS NOT NULL
          AND us_or_international NOT ILIKE 'American'
          AND us_or_international NOT ILIKE 'Other'
      )::numeric
    / NULLIF(COUNT(*), 0),       -- divide by total rows; avoid zero division
  2) AS pct_international
FROM applicants;                  -- AVG/COUNT ignore NULL;