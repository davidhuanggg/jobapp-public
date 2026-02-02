from collections import Counter

def aggregate_job_skills(job_roles: list[list[str]]) -> Counter:
    counter = Counter()
    for skills in job_roles:
        for skill in skills:
            counter[skill.lower()] += 1
    return counter

def compute_skill_gap(resume_skills: list[str], job_skill_counts: Counter):
    resume_set = {s.lower() for s in resume_skills}
    return {
        skill: freq
        for skill, freq in job_skill_counts.items()
        if skill not in resume_set
    }

def rank_skills(skill_gaps: dict, total_jobs: int):
    ranked = {"core": [], "important": [], "optional": []}

    for skill, freq in skill_gaps.items():
        ratio = freq / total_jobs
        if ratio >= 0.7:
            ranked["core"].append(skill)
        elif ratio >= 0.4:
            ranked["important"].append(skill)
        else:
            ranked["optional"].append(skill)

    return ranked

def build_learning_path_for_role(resume_skills, role_skills):
    resume_set = {s.lower() for s in resume_skills}

    missing = [
        s.lower() for s in role_skills
        if s.lower() not in resume_set
    ]

    if not missing:
        return {"core": [], "important": [], "optional": []}

    n = len(missing)

    return {
        "core": missing[: max(1, n // 3)],
        "important": missing[max(1, n // 3): max(2, n // 3)],
        "optional": missing[max(2, n // 3):]
    }
