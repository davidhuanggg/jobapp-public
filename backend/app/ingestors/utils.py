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


# Single-token noise (title + job body token pass).
_TOKEN_STOPWORDS: frozenset[str] = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "you",
        "our",
        "are",
        "will",
        "this",
        "that",
        "from",
        "your",
        "have",
        "has",
        "all",
        "any",
        "can",
        "may",
        "not",
        "but",
        "what",
        "who",
        "how",
        "work",
        "team",
        "job",
        "role",
        "looking",
        "join",
        "years",
        "year",
        "experience",
        "strong",
        "excellent",
        "good",
        "great",
        "senior",
        "junior",
        "remote",
        "full",
        "time",
        "based",
        "opportunity",
        "company",
        "about",
        "apply",
        "today",
    }
)


def extract_job_match_signals(description_html_or_text: str, title: str = "") -> list[str]:
    """
    Build a deduped list of strings to treat as "job-side skills" for resume matching.

    Combines HTML phrase extraction, title tokens, and tech-like single tokens
    (python, aws, c++, etc.) from description + title.
    """
    signals: set[str] = set()
    desc = description_html_or_text or ""

    for s in extract_skills_from_html(desc):
        if s and len(s) >= 2:
            signals.add(s)

    text = extract_text(desc)
    combined = f"{(title or '').lower()} {text}"

    # Tech / stack tokens (letters + digits + common punctuation in skill names).
    for m in re.finditer(r"\b[a-z][a-z0-9+#.]{1,24}\b", combined):
        tok = m.group(0).strip(".")
        if tok in _TOKEN_STOPWORDS or len(tok) < 2:
            continue
        signals.add(tok)

    # Title words (handles "Backend Engineer", "ML Infra", etc.).
    for m in re.finditer(r"[a-z][a-z0-9+#.]{1,24}", (title or "").lower()):
        tok = m.group(0)
        if tok in _TOKEN_STOPWORDS or len(tok) < 2:
            continue
        signals.add(tok)

    return list(signals)

