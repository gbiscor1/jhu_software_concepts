SELECT
  COUNT(*) AS jhu_ms_cs_count
FROM applicants
WHERE
  -- University: raw OR LLM OR in program field
  (
       COALESCE(university,'')               ILIKE '%johns hopkins%'
    OR COALESCE(university,'')               ILIKE '%john hopkins%'
    OR COALESCE(university,'')               ~*   E'\\mJHU\\M'
    OR COALESCE(llm_generated_university,'') ILIKE '%johns hopkins%'
    OR COALESCE(llm_generated_university,'') ILIKE '%john hopkins%'
    OR COALESCE(llm_generated_university,'') ~*   E'\\mJHU\\M'
    OR program ILIKE '%johns hopkins%'
    OR program ILIKE '%john hopkins%'
    OR program ~*   E'\\mJHU\\M'
  )
  AND
  -- Program: Computer Science
  (
       COALESCE(llm_generated_program,'')    ILIKE '%computer science%'
    OR COALESCE(llm_generated_program,'')    ~*   E'\\mCS\\M'
    OR program ILIKE '%computer science%'
    OR program ~*   E'computer\\W*science'
    OR program ~*   E'\\mCS\\M'
  )
  AND
  -- Degree: Master's (MS / Master)
  (
       degree  ILIKE '%master%'
    OR degree  ~*   E'\\mM\\.?S\\.?\\M'
    OR program ILIKE '%master%'
    OR program ~*   E'\\mM\\.?S\\.?\\M'
  );