--Q:10 JHU GPA comparison: Medicine vs Engineering vs Other

WITH jhu AS (
  SELECT
    CASE
      WHEN (
        COALESCE(llm_generated_program,'') ILIKE '%medicine%'
        OR program ILIKE '%medicine%'
      ) THEN 'Medicine'
      WHEN (
        COALESCE(llm_generated_program,'') ILIKE '%engineering%'
        OR program ILIKE '%engineering%'
      ) THEN 'Engineering'
      ELSE 'Other'
    END AS domain_bucket,
    gpa
  FROM applicants
  WHERE
    -- EITHER LLM-generated university OR raw university matches JHU
    (
      COALESCE(llm_generated_university,'') ILIKE '%johns hopkins%'
      OR COALESCE(llm_generated_university,'') ILIKE '%john hopkins%'
      OR COALESCE(llm_generated_university,'') ILIKE '%jhu%'
      OR COALESCE(university,'') ILIKE '%johns hopkins%'
      OR COALESCE(university,'') ILIKE '%john hopkins%'
      OR COALESCE(university,'') ILIKE '%jhu%'
    )
    AND gpa IS NOT NULL
)
SELECT
  domain_bucket,
  COUNT(*)                                    AS n_rows,
  ROUND(AVG(gpa)::numeric, 2)                 AS avg_gpa,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY gpa)::numeric, 2) AS median_gpa
FROM jhu
GROUP BY domain_bucket
ORDER BY domain_bucket;
