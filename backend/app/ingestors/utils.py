import re
from bs4 import BeautifulSoup

COMMON_STOP_PHRASES = {
    "responsibilities",
    "requirements",
    "qualifications",
    "preferred qualifications",
    "about you",
    "job description",
    "what you will do",
    "who you are",
}

def extract_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.get_text(" ").lower()


def extract_skill_candidates(text: str) -> list[str]:
    """
    Extract noun-phrase-like skill candidates from job text.
    Industry agnostic.
    """
    candidates = []

    pattern = re.compile(r"\b[a-z][a-z\s]{2,40}\b")

    for match in pattern.findall(text):
        phrase = match.strip()

        if phrase in COMMON_STOP_PHRASES:
            continue
        if len(phrase.split()) > 5:
            continue
        if phrase.isdigit():
            continue

        candidates.append(phrase)

    return candidates


def normalize_skill(skill: str) -> str:
    skill = skill.strip().lower()

    replacements = {
        "experience with": "",
        "experience in": "",
        "knowledge of": "",
        "hands on": "",
        "hands-on": "",
        "proficient in": "",
        "ability to": "",
    }

    for k, v in replacements.items():
        skill = skill.replace(k, v)

    skill = re.sub(r"\s+", " ", skill)
    return skill


def extract_skills_from_html(html: str) -> list[str]:
    text = extract_text(html)
    raw = extract_skill_candidates(text)
    normalized = [normalize_skill(s) for s in raw]
    return list(set(normalized))


def _collect_tech_tokens(combined_lower: str, title_lower: str) -> list[str]:
    """Raw word-like tokens from job body + title (tech / stack shaped)."""
    out: list[str] = []
    for m in re.finditer(r"\b[a-z][a-z0-9+#.]{1,24}\b", combined_lower):
        t = m.group(0).strip(".")
        if len(t) >= 2:
            out.append(t)
    for m in re.finditer(r"[a-z][a-z0-9+#.]{1,24}", title_lower):
        t = m.group(0)
        if len(t) >= 2:
            out.append(t)
    return out


def extract_job_match_signals(
    description_html_or_text: str,
    title: str = "",
    resume_skills: list[str] | None = None,
) -> list[str]:
    """
    Build strings to treat as "job-side skills" for resume matching.

    Always includes phrase-like extractions from the description HTML/text.

    Single-token tech candidates are **filtered against the user's resume** when
    ``resume_skills`` is provided: only tokens that share the same dynamic
    cluster / normalization as a resume skill are kept (same idea as job matching).

    Without resume context, only longer tokens (>= 5 chars) are kept from the regex
    pass to reduce common short words—no hardcoded stopword list.
    """
    signals: set[str] = set()
    desc = description_html_or_text or ""

    for s in extract_skills_from_html(desc):
        if s and len(s) >= 2:
            signals.add(s)

    text = extract_text(desc)
    title_l = (title or "").lower()
    combined = f"{title_l} {text}"
    candidates = _collect_tech_tokens(combined, title_l)
    unique_toks = sorted(set(candidates))

    if not resume_skills:
        for t in unique_toks:
            if len(t) >= 5:
                signals.add(t)
        return list(signals)

    rs = [s for s in resume_skills if s and str(s).strip()]
    if not rs:
        for t in unique_toks:
            if len(t) >= 5:
                signals.add(t)
        return list(signals)

    # One batch cluster map: resume skills + every distinct job token.
    from app.services.skill_normalize import build_dynamic_cluster_map, normalize_skill_for_match

    cmap = build_dynamic_cluster_map([*rs, *unique_toks])
    resume_canon = {
        normalize_skill_for_match(s, cmap)
        for s in rs
        if normalize_skill_for_match(s, cmap)
    }
    for t in unique_toks:
        ck = normalize_skill_for_match(t, cmap)
        if ck and ck in resume_canon:
            signals.add(ck)

    return list(signals)

