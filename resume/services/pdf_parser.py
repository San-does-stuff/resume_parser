"""
pdf_parser.py

Reads a PDF resume, pulls out the raw text, and then tries to find useful
pieces of information in that text: name, email, phone, skills, education,
experience, projects, and certifications.

This file does NOT use any fancy libraries beyond "re" (regular
expressions) plus pdfplumber/PyPDF2 for reading the PDF itself.
"""

import re


# --- Patterns used to find emails, phone numbers, and years -----------------

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(?\d{2,4}\)?[\s\-]?)?\d{3,4}[\s\-]?\d{3,4}")
YEAR_PATTERN = re.compile(r"(19|20)\d{2}")


# --- Words that usually appear as section titles on a resume ---------------

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "competencies", "tech stack"],
    "education": ["education", "academic", "qualification"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "projects": ["projects", "personal projects"],
    "certifications": ["certifications", "certificates", "licenses"],
}


# --- Big list of known skill words/phrases we try to detect -----------------
# Grouped into sections just to make the list easier to read and update.

SKILLS_LIST = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "ruby", "php", "swift", "kotlin", "go", "rust", "scala", "r",
    "matlab", "perl", "dart", "bash", "shell", "vba",

    # Web Frameworks & Libraries
    "django", "flask", "fastapi", "react", "angular", "vue",
    "node.js", "nodejs", "express", "spring", "laravel",
    "asp.net", "next.js", "jquery", "bootstrap", "tailwind",

    # Databases
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis",
    "cassandra", "oracle", "firebase", "dynamodb",

    # Data Science / ML / AI
    "machine learning", "deep learning", "nlp",
    "natural language processing", "computer vision",
    "data science", "data analysis", "data mining",
    "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "matplotlib", "seaborn",
    "opencv", "nltk", "spacy",

    # Cloud & DevOps
    "aws", "azure", "google cloud", "gcp", "docker",
    "kubernetes", "jenkins", "ci/cd", "terraform",
    "ansible", "linux", "nginx",

    # Version Control
    "git", "github", "gitlab", "bitbucket",

    # Other Tools & Skills
    "rest api", "graphql", "microservices", "agile", "scrum",
    "jira", "excel", "power bi", "tableau",
    "html", "css", "figma", "photoshop",
    "android", "ios", "unity", "wordpress",
    "networking", "cybersecurity", "ethical hacking",
    "autocad", "solidworks",
    "accounting", "tally", "sap",

    # Added from structured_resume_dataset.csv
    "html5", "css3", "xml", "json", "xhtml",
    "ajax", "jquery ui", "js",
    "spring boot", "spring mvc", "spring framework", "angularjs", "angular js",
    "asp.net mvc", "hibernate", "j2ee", "jsp", "servlets", "struts",
    "jpa", "ejb", "jsf", "jstl", "ado.net", "vb.net", "c#.net",
    "springboot", "oracle apex", "apex",
    "sql server", "microsoft sql server", "ms sql server", "db2", "teradata",
    "pl/sql", "t-sql", "stored procedures", "triggers",
    "ssis", "ssrs", "ssas", "sql developer", "sql profiler",
    "hive", "hadoop", "spark", "kafka", "etl", "informatica", "sqoop", "pig",
    "ec2", "s3", "lambda", "rds", "vpc", "iam", "sns", "sqs",
    "puppet", "chef", "prometheus", "grafana", "splunk",
    "tomcat", "jboss", "weblogic", "websphere", "iis", "apache",
    "svn", "tfs", "cvs", "maven", "gradle",
    "junit", "testing", "qa", "quality assurance", "mockito", "soapui",
    "rest", "soap", "wsdl", "web services",
    "tcp", "udp", "dns", "dhcp", "bgp", "ospf", "eigrp", "nat", "vpn",
    "active directory", "firewalls", "network security", "lan", "wan", "routers", "switches",
    "powershell", "shell scripting", "unix shell scripting",
    "confluence", "sharepoint", "ms office", "microsoft office", "outlook",
    "ms project", "visio", "ms visio", "crystal reports",
    "salesforce", "drupal", "dreamweaver",
    "full stack", "full stack development", "reactjs", "react js", "tailwindcss",
    "project management", "business analysis", "sdlc", "waterfall", "troubleshooting",

    # Added to match the skills used in our training dataset (so resumes
    # using these exact words actually get picked up instead of ignored).

    # QA / Testing tools
    "selenium", "jmeter", "postman", "cypress", "testng", "api testing",
    "manual testing", "automation testing", "regression testing",
    "load testing", "test case design", "bug tracking",

    # Security tools
    "burp suite", "nmap", "metasploit", "wireshark", "siem",
    "penetration testing", "vulnerability assessment", "digital forensics",
    "incident response", "iso 27001", "soc operations",

    # AI / ML / data extras
    "llms", "prompt engineering", "generative ai", "mlops", "airflow",

    # Mobile / game / emerging tech
    "flutter", "react native", "objective-c", "unreal engine",
    "game physics", "app store deployment", "play store deployment",
    "ar kit", "vr development", "embedded c", "arduino", "raspberry pi",
    "iot protocols", "robotics control systems",
    "solidity", "ethereum", "smart contracts", "web3.js", "blockchain architecture",

    # DevOps / cloud extras
    "infrastructure as code", "bash scripting", "linux administration",
    "linux basics", "basic networking", "windows server", "cisco routers",
    "server maintenance", "backup solutions", "backup & recovery",
    "firewall configuration", "hardware troubleshooting", "tcp/ip", "ticketing systems",

    # Database extras
    "database design", "data modeling", "query optimization", "indexing", "replication",

    # Design / UX extras
    "adobe xd", "sketch", "after effects", "wireframing",
    "prototyping", "user research", "interaction design", "design systems",
    "usability testing",

    # Product / project management extras
    "product roadmapping", "stakeholder management", "stakeholder communication",
    "requirement gathering", "user stories", "sprint planning", "risk management",
    "risk assessment", "kpi tracking", "project coordination", "business process mapping",

    # ERP / CRM extras
    "odoo", "dynamics 365", "erp implementation", "crm configuration",
    "crm tools", "workflow automation",

    # Marketing extras
    "seo", "seo basics", "google analytics", "google ads",
    "social media marketing", "email marketing", "marketing automation",
    "hubspot", "a/b testing", "content marketing",

    # Technical writing extras
    "technical writing", "markdown", "docs-as-code", "api documentation",
    "swagger/openapi", "style guides", "content structuring", "editing",

    # Leadership / architecture extras
    "system design", "architecture patterns", "cloud architecture",
    "scalability planning", "code review", "mentoring", "team leadership",
    "technical strategy", "cross-team collaboration", "budgeting",
    "it strategy", "it governance", "itil", "vendor management",
    "systems planning", ".net", "shopify", "magento",
    "plugin development", "theme development", "responsive design",
    "oop",

    # Soft skills that show up a lot in entry-level / internship resumes
    "communication", "teamwork", "problem solving", "research",
    "quick learning",
]


# --- Words/phrases that help us guess education and experience entries -----

DEGREE_HINTS = ("bachelor", "master", "b.sc", "m.sc", "btech", "mtech", "phd", "mba", "bs", "ms", "bsc (hons)")
INSTITUTION_HINTS = ("college", "university", "institute", "school", "faculty", "campus")
EDUCATION_KEYWORDS = ("education", "academic", "qualification", "cgpa", "gpa")

EXPERIENCE_TITLE_HINTS = (
    "dev", "trainee", "traineeship", "intern", "internship",
    "apprentice", "apprenticeship", "co-op", "co-operative",
    "co-operative education", "co-operative education and training",
    "freelance", "freelancer", "self-employed", "self employed",
    "contract", "consulting", "developer", "engineer", "analyst",
    "manager", "consultant", "designer", "administrator", "specialist",
    "mid level", "senior level", "lead", "head", "principal", "chief",
    "director", "supervisor", "coordinator",
)


def extract_text_from_pdf(file_obj):
    """
    Try to read the text out of a PDF file.
    First we try the "pdfplumber" library. If that does not work for some
    reason, we fall back to "PyPDF2" instead.
    """
    text_parts = []

    # First attempt: pdfplumber
    try:
        import pdfplumber

        file_obj.seek(0)
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_parts.append(page_text.strip())

        if text_parts:
            full_text = "\n".join(text_parts)
            return _sanitize_extracted_text(full_text)
    except Exception:
        # If pdfplumber fails for any reason, just move on and try PyPDF2.
        pass

    # Second attempt: PyPDF2
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

    full_text = "\n".join(text_parts)
    return _sanitize_extracted_text(full_text)


def _sanitize_extracted_text(text):
    # Some databases (like PostgreSQL) don't allow NUL bytes in text
    # columns, so we replace them with a space just to be safe.
    return text.replace("\x00", " ")


def parse_resume_text(raw_text):
    """
    Take the raw text pulled from a PDF and try to pull out useful
    information from it: name, email, phone, skills, education,
    experience, projects, and certifications.
    """
    lines = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line:
            lines.append(line)

    lowered_lines = [line.lower() for line in lines]

    email = _extract_first_match(EMAIL_PATTERN, raw_text)
    phone = _extract_first_match(PHONE_PATTERN, raw_text)
    name = _extract_name(lines, email)
    location = _extract_location(lines)

    sections = _extract_sections(lines, lowered_lines)

    skills = _extract_skills(sections.get("skills", []), raw_text)
    education = _extract_education(sections.get("education", []), lines)
    experience = _extract_experience(sections.get("experience", []), lines)
    projects = _extract_bulleted_items(sections.get("projects", []))
    certifications = _extract_bulleted_items(sections.get("certifications", []))

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


def _extract_first_match(pattern, text):
    """Return the first match of a regex pattern"""
    match = pattern.search(text)
    if match:
        return match.group(0).strip()
    return None


def _extract_name(lines, email):
    """
    Guess the person's name.(2-4 words, no digits,
    not the email, and not a word like resume or CV)
    """
    for line in lines[:6]:
        word_count = len(line.split())
        has_digit = any(character.isdigit() for character in line)

        if word_count in (2, 3, 4) and not has_digit:
            lower = line.lower()

            if email and email.lower() in lower:
                continue
            if "curriculum" in lower or "resume" in lower or "cv" in lower:
                continue

            return line

    return None


def _extract_location(lines):
    """looks for a line containing an address or location keyword"""
    location_keywords = ("address", "location", "based in")

    for line in lines:
        lower = line.lower()
        for keyword in location_keywords:
            if keyword in lower:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
                return line

    return None


def _extract_sections(lines, lowered_lines):
    """
    Reads the resume line by line, identifies section by section headings and stores each following
    line under the correct section untill next section is found
    """
    current_section = None
    sections = {}
    for section_name in SECTION_HEADERS:
        sections[section_name] = []

    for index in range(len(lines)):
        line = lines[index]
        lower = lowered_lines[index]

        matched_section = None
        for section_name, headers in SECTION_HEADERS.items():
            for header in headers:
                if _is_section_header_line(line, lower, header):
                    matched_section = section_name
                    break
            if matched_section:
                break

        if matched_section:
            current_section = matched_section
            continue

        if current_section:
            sections[current_section].append(line)

    return sections


def _is_section_header_line(original_line, lowered_line, header):
    """Decide if a single line looks like a section title"""
    stripped = original_line.strip()
    if not stripped:
        return False

    if lowered_line == header or lowered_line.startswith(header + ":"):
        return True

    if lowered_line.startswith(header + " "):
        word_count = len(stripped.split())
        if word_count <= 4:
            return True
        if stripped.isupper():
            return True

    return False


def _extract_skills(skill_lines, raw_text):
    """
    Searches the resume for known skills by checking the Skills section first and 
    then the rest of the resume to find any skills mentioned anywhere
    """
    if skill_lines:
        skill_text = " ".join(skill_lines) + " " + raw_text
    else:
        skill_text = raw_text

    lowered_text = skill_text.lower()
    normalized_text = re.sub(r"[^a-z0-9+#.\- ]+", " ", lowered_text)

    raw_tokens = normalized_text.split()
    tokens = set()
    for token in raw_tokens:
        cleaned_token = token.strip(".,;:()[]{}")
        if cleaned_token:
            tokens.add(cleaned_token)

    found = []
    seen = set()
    for skill in SKILLS_LIST:
        skill_found = False
        if skill in tokens:
            skill_found = True
        elif re.search(r"\b" + re.escape(skill) + r"\b", normalized_text):
            skill_found = True

        if skill_found and skill not in seen:
            found.append(skill)
            seen.add(skill)


    # If no known skills are found, it splits the Skills section into individual items
    # so that useful skills can still be extracted
    if skill_lines and not found:
        inferred = []
        for line in skill_lines:
            pieces = re.split(r"[,|/•\-]", line)
            for piece in pieces:
                piece = piece.strip()
                if piece:
                    inferred.append(piece)
        return inferred[:25]

    return found[:25]


def _extract_education(education_lines, all_lines):
    """Pull out lines that look like education entries (degree, school, etc.)"""
    source = education_lines if education_lines else all_lines

    entries = []
    seen = set()

    for line in source:
        lower = line.lower()

        looks_like_education = False
        for hint in DEGREE_HINTS:
            if re.search(r"\b" + re.escape(hint) + r"\b", lower):
                looks_like_education = True
        for hint in INSTITUTION_HINTS:
            if re.search(r"\b" + re.escape(hint) + r"\b", lower):
                looks_like_education = True
        for hint in EDUCATION_KEYWORDS:
            if re.search(r"\b" + re.escape(hint) + r"\b", lower):
                looks_like_education = True

        if not looks_like_education:
            continue

        cleaned = re.sub(r"\s{2,}", " ", line).strip(" ,;|-")
        if len(cleaned) < 4:
            continue

        dedupe_key = cleaned.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        year_match = YEAR_PATTERN.search(line)
        graduation_year = int(year_match.group(0)) if year_match else None

        entries.append({
            "degree": cleaned,
            "institution": None,
            "field_of_study": None,
            "graduation_year": graduation_year,
        })

    return entries[:5]


def _extract_experience(experience_lines, all_lines):
    """Pull out lines that look like job titles/experience entries."""
    source = experience_lines if experience_lines else all_lines

    entries = []
    seen = set()

    for line in source:
        lower = line.lower()

        has_hint = False
        for hint in EXPERIENCE_TITLE_HINTS:
            if re.search(r"\b" + re.escape(hint) + r"\b", lower):
                has_hint = True

        if not has_hint:
            continue

        normalized = re.sub(r"\s{2,}", " ", line).strip(" ,;|-")
        if not normalized:
            continue

        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)

        entries.append({
            "job_title": normalized,
            "company_name": None,
            "start_date": None,
            "end_date": None,
            "description": None,
        })

    if not entries and experience_lines:
        for line in experience_lines:
            normalized = re.sub(r"\s{2,}", " ", line).strip(" ,;|-")

            if len(normalized) < 3:
                continue
            if not re.search(r"[a-zA-Z]", normalized):
                continue
            if re.fullmatch(r"[\w\s,./-]*\b(19|20)\d{2}\b[\w\s,./-]*", normalized):
                continue

            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)

            entries.append({
                "job_title": normalized,
                "company_name": None,
                "start_date": None,
                "end_date": None,
                "description": None,
            })

    return entries[:8]


def _extract_bulleted_items(lines):
    """Removes bullet points and numbering from the beginning of each line 
       to make the text clean and easy to process"""
    cleaned = []
    for line in lines:
        item = re.sub(r"^[•\-\*\d\.\)\s]+", "", line).strip()
        if item:
            cleaned.append(item)
    return cleaned[:10]


def looks_like_resume(parsed_data, raw_text):
    """
    Checks whether the uploaded PDF looks like a resume by looking for common resume details
    such as contact information, skills, education, or work experience before processing it further
    """
    if not raw_text or len(raw_text.strip()) < 50:
        return False

    personal_info = parsed_data.get("personal_info", {})
    has_contact_info = bool(personal_info.get("email")) or bool(personal_info.get("phone"))

    has_skills = len(parsed_data.get("skills", [])) >= 2
    has_education = len(parsed_data.get("education", [])) >= 1
    has_experience = len(parsed_data.get("experience", [])) >= 1

    # A real resume will almost always match at least one of these.
    if has_contact_info or has_skills or has_education or has_experience:
        return True

    return False