from collections import Counter, defaultdict

from app.services.skill_normalize import (
    build_dynamic_cluster_map,
    normalize_skill_for_match,
)


def aggregate_job_skills(
    job_roles: list[list[str]],
    cluster_map: dict[str, str] | None = None,
) -> Counter:
    if cluster_map is None:
        flat = [s for row in job_roles for s in row]
        cluster_map = build_dynamic_cluster_map(flat)
    counter: Counter = Counter()
    for skills in job_roles:
        for skill in skills:
            k = normalize_skill_for_match(skill, cluster_map)
            if k:
                counter[k] += 1
    return counter


def compute_skill_gap(
    resume_skills: list[str],
    job_skill_counts: Counter,
    cluster_map: dict[str, str] | None = None,
):
    if cluster_map is None:
        cluster_map = build_dynamic_cluster_map([*resume_skills, *list(job_skill_counts.keys())])
    resume_set = {
        normalize_skill_for_match(s, cluster_map)
        for s in resume_skills
        if normalize_skill_for_match(s, cluster_map)
    }
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

def build_learning_path_for_role(
    resume_skills,
    role_skills,
    *,
    cluster_map: dict[str, str] | None = None,
):
    if cluster_map is None:
        cluster_map = build_dynamic_cluster_map([*resume_skills, *role_skills])
    resume_set = {
        normalize_skill_for_match(s, cluster_map)
        for s in resume_skills
        if normalize_skill_for_match(s, cluster_map)
    }

    missing: list[str] = []
    seen: set[str] = set()
    for s in role_skills:
        k = normalize_skill_for_match(s, cluster_map)
        if not k or k in resume_set or k in seen:
            continue
        seen.add(k)
        missing.append((s or "").strip())

    if not missing:
        return {"core": [], "important": [], "optional": []}

    n = len(missing)

    return {
        "core": missing[: max(1, n // 3)],
        "important": missing[max(1, n // 3): max(2, n // 3)],
        "optional": missing[max(2, n // 3):]
    }


def build_skill_role_relevance(
    role_skill_rows: list[tuple[str, list[str]]],
    resume_skills: list[str] | None = None,
    *,
    cluster_map: dict[str, str] | None = None,
) -> dict:
    """
    For each skill mentioned in role requirements, aggregate which roles include it
    and assign high/medium/low emphasis (no per-skill counts in the response).

    `skills_to_focus_on` lists resume gaps with the strongest cross-role emphasis first.

    role_skill_rows: (role_title, skills_for_that_role) from extract_job_skills per role.
    """
    if cluster_map is None:
        all_s = list(resume_skills or [])
        for _, skills in role_skill_rows:
            all_s.extend(skills or [])
        cluster_map = build_dynamic_cluster_map(all_s)

    skill_to_roles: dict[str, set[str]] = defaultdict(set)
    skill_display: dict[str, str] = {}

    for role_title, skills in role_skill_rows:
        seen_in_role: set[str] = set()
        for s in skills or []:
            raw = (s or "").strip()
            if not raw:
                continue
            norm = normalize_skill_for_match(raw, cluster_map)
            if not norm or norm in seen_in_role:
                continue
            seen_in_role.add(norm)
            skill_to_roles[norm].add(role_title)
            prev = skill_display.get(norm)
            if prev is None or len(raw) < len(prev):
                skill_display[norm] = raw

    def _focus_note(emphasis: str) -> str:
        if emphasis == "high":
            return (
                "Shows up across most of your recommended roles — not on your resume; "
                "strong leverage if you build this next."
            )
        if emphasis == "medium":
            return (
                "Shows up in several recommended roles — not on your resume yet; "
                "worth prioritizing for flexibility."
            )
        return (
            "Mentioned for some recommended roles — not on your resume; "
            "consider after higher-demand gaps."
        )

    n_roles = len(role_skill_rows)
    emphasis_rank = {"high": 0, "medium": 1, "low": 2}
    row_build: list[tuple[int, dict]] = []
    for norm, role_set in skill_to_roles.items():
        count = len(role_set)
        ratio = count / n_roles if n_roles else 0.0
        if ratio >= 0.6:
            emphasis = "high"
        elif ratio >= 0.35:
            emphasis = "medium"
        else:
            emphasis = "low"
        row_build.append(
            (
                count,
                {
                    "skill": skill_display[norm],
                    "skill_normalized": norm,
                    "roles": sorted(role_set),
                    "emphasis": emphasis,
                },
            )
        )

    row_build.sort(key=lambda x: (-x[0], x[1]["skill"].lower()))
    rows = [r for _, r in row_build]

    your_skills: list[dict] = []
    if resume_skills:
        by_norm = {r["skill_normalized"]: r for r in rows}
        seen_resume: set[str] = set()
        for s in resume_skills:
            k = normalize_skill_for_match(s, cluster_map)
            if not k or k in seen_resume or k not in by_norm:
                continue
            seen_resume.add(k)
            r = by_norm[k]
            your_skills.append(
                {
                    "skill": (s or "").strip(),
                    "roles": r["roles"],
                    "emphasis": r["emphasis"],
                }
            )
        your_skills.sort(
            key=lambda x: (emphasis_rank.get(x["emphasis"], 3), x["skill"].lower())
        )

    # Learning priorities: skills you don't list yet but many recommended roles want
    resume_set = {
        normalize_skill_for_match(s, cluster_map)
        for s in (resume_skills or [])
        if normalize_skill_for_match(s, cluster_map)
    }
    skills_to_focus: list[dict] = []
    for r in rows:
        norm = r["skill_normalized"]
        if norm in resume_set:
            continue
        skills_to_focus.append(
            {
                "skill": r["skill"],
                "roles": list(r["roles"]),
                "emphasis": r["emphasis"],
                "focus_note": _focus_note(r["emphasis"]),
            }
        )
    skills_to_focus.sort(
        key=lambda x: (emphasis_rank.get(x["emphasis"], 3), x["skill"].lower())
    )

    for r in rows:
        r.pop("skill_normalized", None)

    return {
        "roles_considered": n_roles,
        "by_skill": rows,
        "your_skills_in_demand": your_skills,
        "skills_to_focus_on": skills_to_focus,
    }
