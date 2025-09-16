INSERT INTO applicants (
  p_id,                                   
  program, university, comments, date_added, url, status, term,
  us_or_international, gpa, gre, gre_v, gre_aw, degree,
  llm_generated_program, llm_generated_university
) VALUES (
  %(p_id)s,                                
  %(program)s, %(university)s, %(comments)s, %(date_added)s, %(url)s, %(status)s, %(term)s,
  %(us_or_international)s, %(gpa)s, %(gre)s, %(gre_v)s, %(gre_aw)s, %(degree)s,
  %(llm_generated_program)s, %(llm_generated_university)s
)
ON CONFLICT (url) DO NOTHING;