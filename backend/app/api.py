from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.extractor_service import extract_resume_data
from app.services.recommendation_service import get_recommendations, explain_role, extract_career_level
from app.db.crud import save_resume, get_resume
from app.db.database import SessionLocal
from app.models.resume_models import RecommendationResponse
from app.services.job_skill_service import extract_job_skills
from app.services.skill_gap_service import (
    aggregate_job_skills,
    compute_skill_gap,
    rank_skills,
    build_learning_path_for_role,
    build_skill_role_relevance,
)
from app.services.skill_normalize import build_dynamic_cluster_map, collect_strings_for_clustering
from app.services.job_service import match_role_titles_to_jobs
from app.services.learning_resource_service import (
    build_learning_resources,
    get_certifications_for_all_roles,
)
from app.services.roadmap_service import build_focused_role_roadmap
from pydantic import BaseModel

router = APIRouter()


class MatchJobsRequest(BaseModel):
    resume_id: int | None = None
    role_titles: list[str] | None = None


class LearningPathsRequest(BaseModel):
    """Request learning paths for a saved resume."""

    resume_id: int
    role_titles: list[str] | None = None


class LearningResourcesRequest(BaseModel):
    """Strict: must match a resume row from your own `/parse-and-recommend` flow."""

    resume_id: int
    role_titles: list[str] | None = None


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/parse-and-recommend")
async def parse_and_recommend(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    resume_data = await extract_resume_data(file)
    if not resume_data:
        raise HTTPException(400, "Failed to parse resume")

    resume_skills = resume_data.get("skills", [])
    education = resume_data.get("education", {})
    work_experience = resume_data.get("work_experience", [])

    if not resume_skills:
        raise HTTPException(400, "No skills extracted from resume")

    career_info = extract_career_level(
        raw_text=resume_data.get("raw_text", ""),
        work_experience=work_experience if isinstance(work_experience, list) else [],
        education=education if isinstance(education, list) else [],
    )

    # Default null YoE to 0.0 for levels that imply little/no experience so
    # that YoE-based filtering is never bypassed for entry-level candidates.
    if (
        career_info.get("years_of_experience") is None
        and career_info.get("career_level") in ("apprenticeship", "intern", "entry")
    ):
        career_info["years_of_experience"] = 0.0

    resume_data["years_of_experience"] = career_info["years_of_experience"]
    resume_data["career_level"] = career_info["career_level"]
    resume_data["is_student"] = career_info["is_student"]

    try:
        saved_resume = save_resume(db, resume_data)
    except ValueError:
        raise HTTPException(409, "Resume already uploaded")

    recommendations = get_recommendations(
        skills=resume_skills,
        education=education,
        work_experience=work_experience,
        career_level=career_info.get("career_level"),
        years_of_experience=career_info.get("years_of_experience"),
    )

    roles = recommendations.get("recommended_roles", [])

    for role in roles:
        role["detailed_explanation"] = explain_role(
            role["title"],
            years_of_experience=career_info.get("years_of_experience"),
        )

    return {
        "resume_id": saved_resume.id,
        "career_profile": {
            "career_level": career_info["career_level"],
            "years_of_experience": career_info["years_of_experience"],
            "is_student": career_info["is_student"],
        },
        "recommendations": roles,
    }


@router.post("/jobs/match")
async def match_jobs_to_roles(body: MatchJobsRequest, db: Session = Depends(get_db)):
    """
    Find real job postings that match the given role titles.
    Uses job board APIs (e.g. Adzuna) and official company career pages (Greenhouse, Lever).

    When ``resume_id`` is provided, each job includes ``requirement_match_pct``
    (0–100), sorted highest first. Jobs whose level is incompatible with the
    candidate's career level (from ``/parse-and-recommend``) are excluded.
    """
    if not body.resume_id and (not body.role_titles or len(body.role_titles) == 0):
        raise HTTPException(400, "Provide either `resume_id` or `role_titles`.")

    resume_skills = None
    candidate_yoe: float | None = None
    candidate_level: str | None = None
    role_titles: list[str] = body.role_titles or []

    if body.resume_id:
        resume = get_resume(db, body.resume_id)
        if not resume:
            raise HTTPException(404, "Resume not found")
        resume_skills = resume.skills or []
        candidate_yoe = getattr(resume, "years_of_experience", None)
        candidate_level = getattr(resume, "career_level", None)

        # If the resume record has no career data (stale record saved before
        # the career extraction pipeline existed), refuse to run unfiltered
        # rather than silently returning every job regardless of YoE.
        if candidate_yoe is None and candidate_level is None:
            raise HTTPException(
                422,
                "Resume has no career profile (career_level and years_of_experience "
                "are both null). Re-upload the resume via /parse-and-recommend to "
                "rebuild the profile, then retry."
            )

        # If role titles aren't provided, generate them from the saved resume.
        if len(role_titles) == 0:
            # Build education/work-experience lists from stored DB relationships.
            education = [
                {"degree": e.degree, "field": e.field, "institution": e.university}
                for e in (resume.education or [])
            ]
            work_experience = [
                {"company": w.company, "title": w.position, "duration": w.duration}
                for w in (resume.work_experience or [])
            ]

            recommendations = get_recommendations(
                skills=resume_skills,
                education=education,
                work_experience=work_experience,
                career_level=candidate_level,
                years_of_experience=candidate_yoe,
            )
            role_titles = [r.get("title") for r in recommendations.get("recommended_roles", []) if r.get("title")]

    if len(role_titles) == 0:
        return {"by_role": {}, "sources_used": []}

    return match_role_titles_to_jobs(
        role_titles,
        jobs_per_role=15,
        include_company_jobs=True,
        country="us",
        candidate_skills=resume_skills,
        candidate_yoe=candidate_yoe,
        candidate_level=candidate_level,
    )


@router.post("/learning-paths")
async def learning_paths_endpoint(body: LearningPathsRequest, db: Session = Depends(get_db)):
    """
    Return learning paths (skill gaps + certifications + skill demand) for a
    saved resume.

    Call this after ``/parse-and-recommend`` to lazy-load the heavier analysis.
    Optionally pass ``role_titles`` to override the auto-generated role list.
    """
    resume = get_resume(db, body.resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume_skills = resume.skills or []
    if not resume_skills:
        return {"learning_paths": {}, "skill_demand_across_recommended_roles": {}}

    role_titles: list[str] = list(body.role_titles or [])
    if not role_titles:
        education = [
            {"degree": e.degree, "field": e.field, "institution": e.university}
            for e in (resume.education or [])
        ]
        work_experience = [
            {"company": w.company, "title": w.position, "duration": w.duration}
            for w in (resume.work_experience or [])
        ]
        recommendations = get_recommendations(
            skills=resume_skills,
            education=education,
            work_experience=work_experience,
            career_level=getattr(resume, "career_level", None),
            years_of_experience=getattr(resume, "years_of_experience", None),
        )
        role_titles = [
            r.get("title") for r in recommendations.get("recommended_roles", [])
            if r.get("title")
        ]

    if not role_titles:
        return {"learning_paths": {}, "skill_demand_across_recommended_roles": {}}

    role_skill_rows: list[tuple[str, list[str]]] = [
        (title, extract_job_skills(title)) for title in role_titles
    ]

    all_skill_strings = collect_strings_for_clustering(resume_skills, role_skill_rows)
    cluster_map = build_dynamic_cluster_map(all_skill_strings)

    learning_paths: dict = {}
    roles_gap_skills: dict[str, list[str]] = {}
    for role_title, role_skills in role_skill_rows:
        path = build_learning_path_for_role(
            resume_skills=resume_skills,
            role_skills=role_skills,
            cluster_map=cluster_map,
        )
        learning_paths[role_title] = path
        roles_gap_skills[role_title] = (
            path.get("core", []) + path.get("important", []) + path.get("optional", [])
        )

    all_certs = get_certifications_for_all_roles(
        roles_gap_skills,
        career_level=getattr(resume, "career_level", None),
        cluster_map=cluster_map,
    )
    for role_title, path in learning_paths.items():
        path["recommended_certifications"] = all_certs.get(role_title, [])

    skill_demand = build_skill_role_relevance(
        role_skill_rows,
        resume_skills=resume_skills,
        cluster_map=cluster_map,
    )

    return {
        "learning_paths": learning_paths,
        "skill_demand_across_recommended_roles": skill_demand,
    }


@router.post("/learning-resources")
async def learning_resources(body: LearningResourcesRequest, db: Session = Depends(get_db)):
    """
    Return learning resources for exactly one saved resume.

    Strict behavior: if `resume_id` does not exist, returns 404. No fallback to
    other rows (avoids cross-user leakage in shared DB). For real multi-tenant
    isolation, add auth and tie resumes to `user_id` / session.
    """
    resume = get_resume(db, body.resume_id)
    if not resume:
        raise HTTPException(404, "Resume not found")

    resume_skills = resume.skills or []
    if not resume_skills:
        return {"learning_resources": {}}

    explicit_role_titles = body.role_titles
    role_titles: list[str] = list(explicit_role_titles or [])
    if len(role_titles) == 0:
        education = [
            {"degree": e.degree, "field": e.field, "institution": e.university}
            for e in (resume.education or [])
        ]
        work_experience = [
            {"company": w.company, "title": w.position, "duration": w.duration}
            for w in (resume.work_experience or [])
        ]
        recommendations = get_recommendations(
            skills=resume_skills,
            education=education,
            work_experience=work_experience,
            career_level=getattr(resume, "career_level", None),
            years_of_experience=getattr(resume, "years_of_experience", None),
        )
        role_titles = [r.get("title") for r in recommendations.get("recommended_roles", []) if r.get("title")]

    role_skill_rows: list[tuple[str, list[str]]] = []
    for role_title in role_titles:
        role_skill_rows.append((role_title, extract_job_skills(role_title)))

    cluster_strings = collect_strings_for_clustering(resume_skills, role_skill_rows)
    cluster_map = build_dynamic_cluster_map(cluster_strings)

    learning_paths: dict = {}
    for role_title, role_skills in role_skill_rows:
        learning_paths[role_title] = build_learning_path_for_role(
            resume_skills=resume_skills,
            role_skills=role_skills,
            cluster_map=cluster_map,
        )

    out: dict = {
        "learning_resources": build_learning_resources(
            learning_paths,
            resume_skills=resume_skills,
            career_level=getattr(resume, "career_level", None),
            personalize=True,
            cluster_map=cluster_map,
        )
    }
    # Ordered gap roadmap only when the client explicitly asks for exactly one role
    if explicit_role_titles is not None and len(explicit_role_titles) == 1:
        only = explicit_role_titles[0]
        if only in learning_paths:
            out["focused_role_roadmap"] = build_focused_role_roadmap(
                only,
                resume_skills,
                learning_paths[only],
            )
    return out

