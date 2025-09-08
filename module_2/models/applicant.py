
# Gabriel Bisco
# 2025-09-07
# Modern Software Concepts in Python
# models/applicant.py
# Purpose:
# Data models for the Module 2 Grad Café scraper.

from dataclasses import dataclass, asdict
from typing import Optional, Literal, Dict, Any

@dataclass
class ApplicantEntry:
    """
    Raw structured record for data/applicant_data.json (assignment 'SHALL' fields).
    Only fields explicitly listed by the assignment are present.

    Required:
      - program: Program Name
      - university: University
      - date_added: Date info was added to Grad Café (e.g., 'YYYY-MM-DD')
      - url: Link to the specific applicant entry
      - status: Applicant Status (e.g., Accepted/Rejected/Interview/Waitlisted)

    Optional (if available):
      - comments
      - accept_date (if Accepted)
      - reject_date (if Rejected)
      - start_term (Semester of Program Start: Fall/Spring/Summer)
      - start_year (Year of Program Start)
      - citizenship (International/American)
      - gre_total, gre_verbal, gre_aw
      - degree (Masters or PhD)
      - gpa
    """
    # ===== Required =====
    program: str
    university: str
    date_added: str
    url: str
    status: str

    # ===== Optional =====
    comments: Optional[str] = None
    accept_date: Optional[str] = None
    reject_date: Optional[str] = None
    start_term: Optional[str] = None
    start_year: Optional[int] = None
    citizenship: Optional[str] = None
    gre_total: Optional[int] = None
    gre_verbal: Optional[int] = None
    gre_aw: Optional[float] = None
    degree: Optional[str] = None
    gpa: Optional[float] = None

    def to_json(self) -> Dict[str, Any]:
        """Stable dict for JSON dumping; missing values remain None."""
        return asdict(self)


@dataclass
class ApplicantEntryExtended(ApplicantEntry):
    """
    Extended record for data/llm_extend_applicant_data.json.
    """
    program_canon: Optional[str] = None
    university_canon: Optional[str] = None
