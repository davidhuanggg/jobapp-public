"""
Ordered learning roadmap for a single target role (gap skills vs resume).

Uses Groq when available to sequence skills for efficient learning; falls back to
foundation → next → stretch from core/important/optional buckets.
"""

from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_GROQ = os.getenv("GROQ_API_KEY")
_client: Groq | None = Groq(api_key=_GROQ) if _GROQ else None
_MODEL = "llama-3.1-8b-instant"


def _extract_json_array(text: str) -> list:
    if not text:
        return []
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def build_focused_role_roadmap(
    role_title: str,
    resume_skills: list[str],
    learning_path: dict,
) -> dict:
    """
    learning_path: { "core": [...], "important": [...], "optional": [...] }
    Returns { "role", "steps": [{ "priority", "skill", "phase", "tip" }], "source": "llm"|"heuristic" }
    """
    core = list(learning_path.get("core") or [])
    important = list(learning_path.get("important") or [])
    optional = list(learning_path.get("optional") or [])
    flat = core + important + optional

    if not flat:
        return {
            "role": role_title,
            "steps": [],
            "note": "No skill gaps for this role compared to your resume.",
            "source": "none",
        }

    if _client:
        steps = _roadmap_llm(role_title, resume_skills, core, important, optional)
        if steps:
            return {"role": role_title, "steps": steps, "source": "llm"}

    return {
        "role": role_title,
        "steps": _roadmap_heuristic(core, important, optional),
        "source": "heuristic",
    }


def _roadmap_heuristic(
    core: list[str],
    important: list[str],
    optional: list[str],
) -> list[dict]:
    steps: list[dict] = []
    p = 1
    for s in core:
        steps.append(
            {
                "priority": p,
                "skill": s,
                "phase": "foundation",
                "tip": "Tackle early — core gap for this role.",
            }
        )
        p += 1
    for s in important:
        steps.append(
            {
                "priority": p,
                "skill": s,
                "phase": "next",
                "tip": "Build after foundations — common expectation for this role.",
            }
        )
        p += 1
    for s in optional:
        steps.append(
            {
                "priority": p,
                "skill": s,
                "phase": "stretch",
                "tip": "Nice to have once core skills are solid.",
            }
        )
        p += 1
    return steps


def _roadmap_llm(
    role_title: str,
    resume_skills: list[str],
    core: list[str],
    important: list[str],
    optional: list[str],
) -> list[dict]:
    rs = ", ".join((s or "").strip() for s in (resume_skills or [])[:40])
    prompt = f"""You are a technical learning coach.

Target role: {role_title}
Candidate already has (sample): {rs or "not listed"}

They must learn these missing skills, grouped as:
- foundation (learn first): {json.dumps(core)}
- next: {json.dumps(important)}
- stretch: {json.dumps(optional)}

Return a SINGLE JSON array only. Each item:
{{ "priority": <int starting at 1>, "skill": "<exact skill string from lists above>", "phase": "foundation"|"next"|"stretch", "tip": "<one short sentence why this order>" }}

Rules:
- Include EVERY skill from the three lists exactly once.
- Order for efficient learning (dependencies and typical hiring expectations).
- priority runs 1..N with no gaps."""

    resp = _client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": "Return JSON array only. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.25,
        max_tokens=1200,
    )
    raw = (resp.choices[0].message.content or "").strip()
    arr = _extract_json_array(raw)
    steps: list[dict] = []
    for i, row in enumerate(arr):
        if not isinstance(row, dict):
            continue
        sk = str(row.get("skill", "")).strip()
        if not sk:
            continue
        steps.append(
            {
                "priority": int(row.get("priority", i + 1)),
                "skill": sk,
                "phase": str(row.get("phase", "next")).lower(),
                "tip": str(row.get("tip", "")).strip() or "Prioritized for this role.",
            }
        )
    # Must cover all skills; if LLM dropped some, append heuristic tail
    covered = {s["skill"].lower() for s in steps}
    all_skills = core + important + optional
    for s in all_skills:
        if s.lower() not in covered:
            steps.append(
                {
                    "priority": len(steps) + 1,
                    "skill": s,
                    "phase": "next",
                    "tip": "Added to complete your roadmap.",
                }
            )
            covered.add(s.lower())
    steps.sort(key=lambda x: x["priority"])
    return steps if steps else []
