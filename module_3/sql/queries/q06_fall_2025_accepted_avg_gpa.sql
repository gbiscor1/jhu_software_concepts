SELECT
  ROUND(AVG(gpa)::numeric, 2) AS avg_gpa_fall2025_accepted
FROM applicants
WHERE
  term ILIKE 'Fall 2025'
  AND status ILIKE 'accept%'
  AND gpa IS NOT NULL;