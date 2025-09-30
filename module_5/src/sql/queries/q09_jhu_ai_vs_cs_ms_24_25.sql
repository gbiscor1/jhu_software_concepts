-- Q9: JHU Master's admits AI vs CS
WITH base AS (
  SELECT
    CASE
      -- AI (Artificial Intelligence / AI / A.I.)
      WHEN (
        COALESCE(llm_generated_program,'') ILIKE '%artificial intelligence%'
        OR COALESCE(llm_generated_program,'') ~* E'\\mAI\\M'
        OR program ILIKE '%artificial intelligence%'
        OR program  ~* E'\\mAI\\M'
        OR program  ~* E'\\mA\\.?I\\.?\\M'
      ) THEN 'AI MS'

      -- CS (Computer Science / CS)
      WHEN (
        COALESCE(llm_generated_program,'') ILIKE '%computer science%'
        OR COALESCE(llm_generated_program,'') ~* E'\\mCS\\M'
        OR program ILIKE '%computer science%'
        OR program  ~* E'\\mCS\\M'
      ) THEN 'CS MS'

      ELSE NULL
    END AS prog_bucket
  FROM applicants
  WHERE
    status ILIKE 'accept%'
    AND degree ILIKE 'Master%'

    -- University: EITHER raw 'university' OR LLM hits
    AND (
         COALESCE(university,'') ILIKE '%johns hopkins%'
      OR COALESCE(university,'') ILIKE '%john hopkins%'
      OR COALESCE(university,'') ILIKE '%jhu%'
      OR COALESCE(llm_generated_university,'') ILIKE '%johns hopkins%'
      OR COALESCE(llm_generated_university,'') ILIKE '%john hopkins%'
      OR COALESCE(llm_generated_university,'') ILIKE '%jhu%'
      OR program  ILIKE '%johns hopkins%'
      OR program  ILIKE '%john hopkins%'
      OR program  ILIKE '%jhu%'
      OR comments ILIKE '%johns hopkins%'
      OR comments ILIKE '%jhu%'
    )

    -- calendar-year window
    AND date_added >= DATE_TRUNC('year', CURRENT_DATE)
    AND date_added <  DATE_TRUNC('year', CURRENT_DATE) + INTERVAL '1 year'
)
SELECT
  prog_bucket AS program_bucket,
  COUNT(*)    AS accepted_count
FROM base
WHERE prog_bucket IS NOT NULL
GROUP BY prog_bucket
ORDER BY program_bucket;
