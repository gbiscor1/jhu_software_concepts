# models/applicant.py

from dataclasses import dataclass, asdict
from typing import Optional, Literal, Dict, Any

# ---- Literals  ----
# TODO: separate literal types into a separate file for usage in other files
Status = Literal["Accepted", "Rejected", "Interview", "Waitlisted", "Pending"]
Degree = Literal["Masters", "PhD", "MFA", "MBA", "JD", "EdD", "PsyD", "Other"]
Term = Literal["Fall", "Spring", "Summer"]
Citizenship = Literal["International", "American"]

@dataclass
class ApplicantEntry:
    """
    Cleaned record for data/applicant_data.json (only SHALL/SHOULD fields).
    """
    # REQUIRED
    program: str
    university: str
    date_added: str           # keep as string (ISO 'YYYY-MM-DD' preferred)
    url: str
    status: Status

    # Optional 
    comments: Optional[str] = None
    accept_date: Optional[str] = None 
    reject_date: Optional[str] = None 
    start_term: Optional[Term] = None
    start_year: Optional[int] = None
    citizenship: Optional[Citizenship] = None
    gre_total: Optional[int] = None
    gre_verbal: Optional[int] = None 
    gre_aw: Optional[float] = None
    degree: Optional[Degree] = None
    gpa: Optional[float] = None 

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ApplicantEntryExtended(ApplicantEntry):
    """
    Extended record for data/llm_extend_applicant_data.json.
    """
    program_canon: Optional[str] = None
    university_canon: Optional[str] = None
