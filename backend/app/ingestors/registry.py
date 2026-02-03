from app.ingestors.greenhouse import ingest_company as gh_ingest
from app.ingestors.lever import ingest_company as lever_ingest

def ingest_all(company: str):
    jobs = []
    jobs.extend(gh_ingest(company))
    jobs.extend(lever_ingest(company))
    return jobs

