CREATE UNIQUE INDEX IF NOT EXISTS applicants_url_key ON applicants (url);

CREATE TABLE IF NOT EXISTS applicants (
  p_id                 INTEGER PRIMARY KEY,
  program              TEXT,
  university           TEXT,
  comments             TEXT,
  date_added           DATE,
  url                  TEXT,
  status               TEXT,
  term                 TEXT,
  us_or_international  TEXT,
  gpa                  FLOAT,
  gre                  FLOAT,
  gre_v                FLOAT,
  gre_aw               FLOAT,
  degree               TEXT,
  llm_generated_program    TEXT,
  llm_generated_university TEXT
);
