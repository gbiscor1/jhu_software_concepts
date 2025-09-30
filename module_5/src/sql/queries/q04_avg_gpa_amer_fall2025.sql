-- Q4 — Average GPA of American applicants for Fall 2025

SELECT
  ROUND(AVG(gpa)::numeric, 2) AS avg_gpa_american_fall_2025
FROM applicants
WHERE
  us_or_international ILIKE 'American'  -- restrict to American applicants
  AND term ILIKE 'Fall 2025'            -- for the Fall 2025 term only
  AND gpa IS NOT NULL;                  -- not NULL gpas