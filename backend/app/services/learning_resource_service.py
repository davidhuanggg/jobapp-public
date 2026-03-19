"""
V1 learning resource matcher.

Given the computed learning paths, returns curated resources per skill.
Keeps learning path structure untouched and provides a separate
`learning_resources` payload.
"""

from __future__ import annotations

from urllib.parse import quote_plus


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


def _normalize_skill(skill: str) -> str:
    return (skill or "").strip().lower()


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


def get_resources_for_skill(skill: str) -> list[dict]:
    normalized = _normalize_skill(skill)
    if not normalized:
        return []
    return RESOURCE_CATALOG.get(normalized, _fallback_resources(normalized))


def build_learning_resources(learning_paths: dict) -> dict:
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

    for role, buckets in (learning_paths or {}).items():
        role_out = {"core": [], "important": [], "optional": []}
        for bucket in ("core", "important", "optional"):
            skills = buckets.get(bucket, []) if isinstance(buckets, dict) else []
            role_out[bucket] = [
                {
                    "skill": s,
                    "resources": get_resources_for_skill(s),
                }
                for s in skills
            ]
        out[role] = role_out

    return out

