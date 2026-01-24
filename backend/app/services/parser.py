from ..extractor.text import extract_text, normalize, split_sections, extract_contact, extract_skills, extract_name
from ..models.resume import Resume, ExperienceItem

def parse_resume(file_path: str) -> Resume:
    raw_text = extract_text(file_path)
    raw_text = normalize(raw_text)
    sections = split_sections(raw_text)
    contact = extract_contact(raw_text)

    return Resume(
        name=extract_name(raw_text),
        email=contact["email"],
        phone=contact["phone"],
        skills=extract_skills(sections.get("skills", raw_text)),
        experience=[],  # Could be extended later
        education=[],   # Could be extended later
        raw_text=raw_text
    )

