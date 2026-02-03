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

