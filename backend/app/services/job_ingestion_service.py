from collections import Counter
from app.ingestors import greenhouse, lever


def ingest_company_jobs(company: str, source: str) -> list[dict]:
    if source == "greenhouse":
        return greenhouse.ingest_company(company)
    if source == "lever":
        return lever.ingest_company(company)

    raise ValueError(f"Unknown ATS source: {source}")


def compute_skill_frequency(jobs: list[dict]) -> dict[str, int]:
    counter = Counter()
    for job in jobs:
        counter.update(job.get("required_skills", []))
    return dict(counter)

