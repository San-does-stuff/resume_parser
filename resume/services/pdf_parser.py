import re
from typing import Any


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}")
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "competencies", "tech stack"],
    "education": ["education", "academic", "qualification"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certifications", "certificates", "licenses"],
}

COMMON_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "sql",
    "html",
    "css",
    "react",
    "django",
    "flask",
    "node",
    "nodejs",
    "aws",
    "docker",
    "kubernetes",
    "git",
    "linux",
    "pandas",
    "numpy",
    "tensorflow",
    "pytorch",
    "tableau",
    "powerbi",
    "mongodb",
    "postgresql",
}

DEGREE_HINTS = ("bachelor", "master", "b.sc", "m.sc", "btech", "mtech", "phd", "mba", "bs", "ms","bsc (hons)")
EXPERIENCE_TITLE_HINTS = (
    "dev",
    "trainee",
    "traineeship",
    "intern",
    "internship",
    "apprentice",
    "apprenticeship",
    "co-op",
    "co-operative",
    "co-operative education",
    "co-operative education and training",
    "developer",
    "engineer",
    "analyst",
    "intern",
    "manager",
    "consultant",
    "designer",
    "administrator",
    "specialist",
    "mid level",
    "senior level",
    "lead",
    "head",
    "principal",
    "chief",
    "manager",
    "director",
    "supervisor",
    "coordinator",
)


def extract_text_from_pdf(file_obj) -> str:
    """
    Extract text from a text-based PDF.
    Tries pdfplumber first, then falls back to PyPDF2.
    """
    text_parts: list[str] = []

    try:
        import pdfplumber

        file_obj.seek(0)
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())
        if text_parts:
            return "\n".join(text_parts)
    except Exception:
        pass

    try:
        from PyPDF2 import PdfReader

        file_obj.seek(0)
        reader = PdfReader(file_obj)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text.strip())
    except Exception:
        return ""

    return "\n".join(text_parts)


def parse_resume_text(raw_text: str) -> dict[str, Any]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    lowered_lines = [line.lower() for line in lines]

    email = _extract_first_match(EMAIL_PATTERN, raw_text)
    phone = _extract_first_match(PHONE_PATTERN, raw_text)
    name = _extract_name(lines, email)
    location = _extract_location(lines)

    sectioned = _extract_sections(lines, lowered_lines)
    skills = _extract_skills(sectioned.get("skills", []), raw_text)
    education = _extract_education(sectioned.get("education", []), lines)
    experience = _extract_experience(sectioned.get("experience", []), lines)
    projects = _extract_bulleted_items(sectioned.get("projects", []))
    certifications = _extract_bulleted_items(sectioned.get("certifications", []))

    return {
        "personal_info": {
            "name": name,
            "email": email,
            "phone": phone,
            "location": location,
        },
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
        "certifications": certifications,
    }


def _extract_first_match(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match else None


def _extract_name(lines: list[str], email: str | None) -> str | None:
    for line in lines[:6]:
        if len(line.split()) in (2, 3, 4) and not any(ch.isdigit() for ch in line):
            lower = line.lower()
            if email and email.lower() in lower:
                continue
            if any(token in lower for token in ("curriculum", "resume", "cv")):
                continue
            return line
    return None


def _extract_location(lines: list[str]) -> str | None:
    location_keywords = ("address", "location", "based in")
    for line in lines:
        lower = line.lower()
        if any(keyword in lower for keyword in location_keywords):
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
            return line
    return None


def _extract_sections(lines: list[str], lowered_lines: list[str]) -> dict[str, list[str]]:
    current_section: str | None = None
    sections: dict[str, list[str]] = {key: [] for key in SECTION_HEADERS}

    for idx, line in enumerate(lines):
        lower = lowered_lines[idx]
        matched_section = None
        for section_name, headers in SECTION_HEADERS.items():
            if any(lower == header or lower.startswith(f"{header}:") for header in headers):
                matched_section = section_name
                break
        if matched_section:
            current_section = matched_section
            continue
        if current_section:
            sections[current_section].append(line)

    return sections


def _extract_skills(skill_lines: list[str], raw_text: str) -> list[str]:
    skill_text = " ".join(skill_lines) if skill_lines else raw_text
    normalized_text = re.sub(r"[^A-Za-z0-9+#.\- ]+", " ", skill_text.lower())
    tokens = {token.strip(".,;:()[]{}") for token in normalized_text.split() if token}

    found = []
    for skill in sorted(COMMON_SKILLS):
        if skill in tokens or re.search(rf"\b{re.escape(skill)}\b", normalized_text):
            found.append(skill)

    if skill_lines and not found:
        inferred = []
        for line in skill_lines:
            pieces = re.split(r"[,|/•\-]", line)
            inferred.extend(piece.strip() for piece in pieces if piece.strip())
        return inferred[:25]

    return found[:25]


def _extract_education(education_lines: list[str], all_lines: list[str]) -> list[dict[str, Any]]:
    source = education_lines or all_lines
    entries: list[dict[str, Any]] = []

    for line in source:
        lower = line.lower()
        if any(hint in lower for hint in DEGREE_HINTS):
            year_match = YEAR_PATTERN.search(line)
            entries.append(
                {
                    "degree": line,
                    "institution": None,
                    "field_of_study": None,
                    "graduation_year": int(year_match.group(0)) if year_match else None,
                }
            )

    return entries[:5]


def _extract_experience(experience_lines: list[str], all_lines: list[str]) -> list[dict[str, Any]]:
    source = experience_lines or all_lines
    entries: list[dict[str, Any]] = []

    for line in source:
        lower = line.lower()
        if any(hint in lower for hint in EXPERIENCE_TITLE_HINTS):
            entries.append(
                {
                    "job_title": line,
                    "company_name": None,
                    "start_date": None,
                    "end_date": None,
                    "description": None,
                }
            )

    return entries[:8]


def _extract_bulleted_items(lines: list[str]) -> list[str]:
    cleaned = []
    for line in lines:
        item = re.sub(r"^[•\-\*\d\.\)\s]+", "", line).strip()
        if item:
            cleaned.append(item)
    return cleaned[:10]
