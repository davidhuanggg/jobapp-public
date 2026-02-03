from typing import TypedDict, List

class NormalizedJob(TypedDict):
    job_id: str
    company: str
    title: str
    normalized_title: str
    seniority: str
    location: str
    remote_type: str
    posting_date: str  # YYYY-MM-DD
    required_skills: List[str]
    ats_type: str
    source_url: str
