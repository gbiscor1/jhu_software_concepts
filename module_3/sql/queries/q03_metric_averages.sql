-- Q3 — Averages for GPA, GRE (quant/total), GRE_V (verbal), GRE_AW (analytical writing).

SELECT
  ROUND(AVG(gpa)::numeric,   2) AS avg_gpa,     -- average GPA across non-NULL gpa
  ROUND(AVG(gre)::numeric,   2) AS avg_gre,     -- average GRE (quant/total) across non-NULL gre
  ROUND(AVG(gre_v)::numeric, 2) AS avg_gre_v,   -- average GRE verbal
  ROUND(AVG(gre_aw)::numeric,2) AS avg_gre_aw   -- average GRE analytical writing
FROM applicants;