-- Q8 — Count 2025 + Accepted + Georgetown + PhD + Computer Science


SELECT
  COUNT(*) AS georgetown_phd_cs_accept_2025
FROM applicants
WHERE
  -- calendar year 2025 window
  date_added >= DATE '2025-01-01'
  AND date_added <  DATE '2026-01-01'

  -- accepted
  AND status ILIKE 'accept%'

  -- university: either raw OR LLM
  AND (
       COALESCE(university,'') ILIKE '%georgetown%'
    OR COALESCE(llm_generated_university,'') ILIKE '%georgetown%'
    OR program  ILIKE '%georgetown%'
    OR comments ILIKE '%georgetown%'
  )

  -- program: Computer Science (LLM and raw)
  AND (
       COALESCE(llm_generated_program,'') ILIKE '%computer science%'
    OR COALESCE(llm_generated_program,'') ~* E'\\mCS\\M'
    OR program ILIKE '%computer science%'
    OR program  ~* E'\\mCS\\M'
  )

  -- degree: PhD 
  AND (
       degree ILIKE '%phd%'
    OR program ILIKE '%phd%'
    OR comments ILIKE '%phd%'
  );
