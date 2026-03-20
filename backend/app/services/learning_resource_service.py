"""
Learning resource matcher.

Given the computed learning paths, returns curated resources per skill.
Uses the static catalog when it matches; optionally calls Groq once per role
to add resume- and role-specific context + tailored search queries (no
hallucinated URLs).
"""

from __future__ import annotations

import json
import os
import re
from urllib.parse import quote_plus

from dotenv import load_dotenv
from groq import Groq

from app.services.skill_normalize import build_dynamic_cluster_map, normalize_skill_for_match

load_dotenv()

_GROQ_KEY = os.getenv("GROQ_API_KEY")
_groq_client: Groq | None = Groq(api_key=_GROQ_KEY) if _GROQ_KEY else None
_GROQ_MODEL = "llama-3.1-8b-instant"


# Curated starter catalog for common skills.
# Expand this over time as you observe user demand.
RESOURCE_CATALOG: dict[str, list[dict]] = {
    "python": [
        {
            "title": "Python Official Tutorial",
            "url": "https://docs.python.org/3/tutorial/",
            "provider": "Python.org",
            "type": "documentation",
            "cost": "free",
        },
        {
            "title": "Automate the Boring Stuff with Python",
            "url": "https://automatetheboringstuff.com/",
            "provider": "Al Sweigart",
            "type": "course/book",
            "cost": "free",
        },
    ],
    "sql": [
        {
            "title": "SQLBolt Interactive SQL Lessons",
            "url": "https://sqlbolt.com/",
            "provider": "SQLBolt",
            "type": "interactive",
            "cost": "free",
        },
        {
            "title": "PostgreSQL Tutorial",
            "url": "https://www.postgresqltutorial.com/",
            "provider": "PostgreSQL Tutorial",
            "type": "tutorial",
            "cost": "free",
        },
    ],
    "docker": [
        {
            "title": "Docker Get Started",
            "url": "https://docs.docker.com/get-started/",
            "provider": "Docker Docs",
            "type": "documentation",
            "cost": "free",
        },
        {
            "title": "Docker Curriculum",
            "url": "https://docker-curriculum.com/",
            "provider": "Docker Curriculum",
            "type": "tutorial",
            "cost": "free",
        },
    ],
    "kubernetes": [
        {
            "title": "Kubernetes Basics",
            "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/",
            "provider": "Kubernetes",
            "type": "documentation",
            "cost": "free",
        }
    ],
    "aws": [
        {
            "title": "AWS Skill Builder",
            "url": "https://explore.skillbuilder.aws/learn",
            "provider": "AWS",
            "type": "course",
            "cost": "free/paid",
        }
    ],
    "fastapi": [
        {
            "title": "FastAPI Tutorial",
            "url": "https://fastapi.tiangolo.com/tutorial/",
            "provider": "FastAPI",
            "type": "documentation",
            "cost": "free",
        }
    ],
    "react": [
        {
            "title": "React Learn",
            "url": "https://react.dev/learn",
            "provider": "React",
            "type": "documentation",
            "cost": "free",
        }
    ],
    "machine learning": [
        {
            "title": "Machine Learning Crash Course",
            "url": "https://developers.google.com/machine-learning/crash-course",
            "provider": "Google",
            "type": "course",
            "cost": "free",
        }
    ],
}

# Map fuzzy canonical keys from normalize_skill_for_match -> RESOURCE_CATALOG keys
_CANONICAL_TO_CATALOG: dict[str, str] = {
    "python": "python",
    "sql": "sql",
    "postgresql": "sql",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "aws": "aws",
    "fastapi": "fastapi",
    "react": "react",
    "machinelearning": "machine learning",
}


def _fallback_resources(skill: str) -> list[dict]:
    query = quote_plus(skill)
    return [
        {
            "title": f"{skill} official documentation and guides",
            "url": f"https://www.google.com/search?q={query}+official+documentation",
            "provider": "Web",
            "type": "documentation",
            "cost": "free",
        },
        {
            "title": f"{skill} hands-on exercises",
            "url": f"https://www.kaggle.com/search?q={query}",
            "provider": "Kaggle",
            "type": "practice",
            "cost": "free",
        },
        {
            "title": f"{skill} structured courses",
            "url": f"https://www.coursera.org/search?query={query}",
            "provider": "Coursera",
            "type": "course",
            "cost": "free",
        },
    ]


def get_resources_for_skill(
    skill: str,
    cluster_map: dict[str, str] | None = None,
) -> list[dict]:
    raw = (skill or "").strip()
    if not raw:
        return []
    lit = raw.lower()
    if lit in RESOURCE_CATALOG:
        return RESOURCE_CATALOG[lit]
    canon = normalize_skill_for_match(raw, cluster_map)
    cat_key = _CANONICAL_TO_CATALOG.get(canon)
    if cat_key and cat_key in RESOURCE_CATALOG:
        return RESOURCE_CATALOG[cat_key]
    return _fallback_resources(raw)


def _extract_json_object(text: str) -> dict | None:
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def _personalize_skills_for_role(
    role_title: str,
    resume_skills: list[str],
    gap_skills: list[str],
    *,
    cluster_map: dict[str, str] | None = None,
) -> dict[str, dict]:
    """
    One Groq call per role. Maps normalized skill -> {why_this_matters, search_queries}.
    Returns {} if API unavailable or on failure.
    """
    if not _groq_client or not gap_skills:
        return {}

    # Keep prompt bounded
    rs = ", ".join((s or "").strip() for s in (resume_skills or [])[:35])
    gaps = list(dict.fromkeys(g.strip() for g in gap_skills if g and g.strip()))[:20]
    if not gaps:
        return {}

    prompt = f"""You tailor learning plans for job seekers.

Candidate resume skills (sample): {rs or "(none listed)"}
Target role: {role_title}
Skills they still need to learn (gaps): {json.dumps(gaps)}

For EACH gap skill, write a short rationale and 2–3 web search queries that would find
high-quality official docs, courses, or tutorials. Do NOT invent URLs.

Return JSON only, shape:
{{
  "per_skill": [
    {{
      "skill": "<exact string from gaps list>",
      "why_this_matters": "<1-2 sentences tying this skill to their background and the role>",
      "search_queries": ["<query1>", "<query2>", "<query3>"]
    }}
  ]
}}
Include one object per gap skill; use the exact skill strings from the gaps list."""

    try:
        response = _groq_client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You return valid JSON only. No markdown fences.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1200,
        )
        raw = (response.choices[0].message.content or "").strip()
        data = _extract_json_object(raw) or {}
        rows = data.get("per_skill") or []
        out: dict[str, dict] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            sk = normalize_skill_for_match(str(row.get("skill", "")), cluster_map)
            if not sk:
                continue
            why = str(row.get("why_this_matters", "")).strip()
            queries = row.get("search_queries") or []
            if not isinstance(queries, list):
                queries = []
            queries = [str(q).strip() for q in queries if str(q).strip()][:3]
            out[sk] = {"why_this_matters": why, "search_queries": queries}
        return out
    except Exception:
        return {}


def _merge_catalog_and_personalization(
    skill: str,
    catalog_or_fallback: list[dict],
    personal: dict | None,
) -> list[dict]:
    """Prepend context note + tailored search links, then catalog/fallback. Dedupe URLs."""
    merged: list[dict] = []
    seen_urls: set[str] = set()

    if personal:
        why = personal.get("why_this_matters", "").strip()
        if why:
            merged.append(
                {
                    "title": "Why this skill for you",
                    "url": None,
                    "provider": "Personalized",
                    "type": "context",
                    "cost": "n/a",
                    "context": why,
                }
            )
        for q in personal.get("search_queries", [])[:3]:
            qp = quote_plus(q)
            url = f"https://www.google.com/search?q={qp}"
            if url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(
                {
                    "title": f"Tailored search: {q[:100]}",
                    "url": url,
                    "provider": "Web",
                    "type": "search",
                    "cost": "free",
                }
            )

    for r in catalog_or_fallback:
        url = r.get("url")
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        merged.append(r)

    return merged


def build_learning_resources(
    learning_paths: dict,
    *,
    resume_skills: list[str] | None = None,
    personalize: bool = True,
    cluster_map: dict[str, str] | None = None,
) -> dict:
    """
    learning_paths input shape:
    {
      "Role Name": {"core": [skill], "important": [skill], "optional": [skill]}
    }

    output shape:
    {
      "Role Name": {
        "core": [{"skill": "...", "resources": [...]}, ...],
        "important": [...],
        "optional": [...]
      }
    }
    """
    out: dict = {}
    rs = resume_skills or []

    for role, buckets in (learning_paths or {}).items():
        gap_skills: list[str] = []
        if isinstance(buckets, dict):
            for bucket in ("core", "important", "optional"):
                gap_skills.extend(buckets.get(bucket, []) or [])
        personal_by_skill: dict[str, dict] = {}
        cm = cluster_map
        if cm is None:
            cm = build_dynamic_cluster_map([*rs, *gap_skills])

        if personalize and rs:
            personal_by_skill = _personalize_skills_for_role(
                role, rs, gap_skills, cluster_map=cm
            )

        role_out = {"core": [], "important": [], "optional": []}
        for bucket in ("core", "important", "optional"):
            skills = buckets.get(bucket, []) if isinstance(buckets, dict) else []
            role_out[bucket] = []
            for s in skills:
                norm = normalize_skill_for_match(s, cm)
                base = get_resources_for_skill(s, cm)
                personal = personal_by_skill.get(norm) if personal_by_skill else None
                resources = (
                    _merge_catalog_and_personalization(s, base, personal)
                    if personal
                    else base
                )
                role_out[bucket].append({"skill": s, "resources": resources})
        out[role] = role_out

    return out

