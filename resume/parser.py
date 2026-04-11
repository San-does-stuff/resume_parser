# resume/parser.py
# ============================================================
# Complete Resume Parser
# PDF extraction  : pdfplumber
# All other logic : pure Python (re, os) — built from scratch
# ============================================================

import re
import os


# ════════════════════════════════════════════════════════════
# PART 1 — TEXT EXTRACTION
# ════════════════════════════════════════════════════════════

def extract_text_from_pdf(file_path):
    """Extract all text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
        text = ''
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + '\n'
        return text.strip()
    except Exception as e:
        print(f'pdfplumber error: {e}')
        return ''


def read_txt_file(file_path):
    """Read a plain text file trying multiple encodings."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                return f.read()
        except:
            continue
    return ''


def extract_text(file_path):
    """
    Auto-detect file type and extract text.
    Supports: PDF, TXT
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.txt':
        return read_txt_file(file_path)
    else:
        return read_txt_file(file_path)


# ════════════════════════════════════════════════════════════
# PART 2 — SKILLS DICTIONARY
# ════════════════════════════════════════════════════════════

SKILLS_LIST = [
    # Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c', 'c++', 'c#',
    'ruby', 'php', 'swift', 'kotlin', 'go', 'rust', 'scala', 'r',
    'matlab', 'perl', 'dart', 'bash', 'shell', 'vba',

    # Web Frameworks & Libraries
    'django', 'flask', 'fastapi', 'react', 'angular', 'vue',
    'node.js', 'nodejs', 'express', 'spring', 'laravel',
    'asp.net', 'next.js', 'jquery', 'bootstrap', 'tailwind',

    # Databases
    'sql', 'mysql', 'postgresql', 'sqlite', 'mongodb', 'redis',
    'cassandra', 'oracle', 'firebase', 'dynamodb',

    # Data Science / ML / AI
    'machine learning', 'deep learning', 'nlp',
    'natural language processing', 'computer vision',
    'data science', 'data analysis', 'data mining',
    'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'seaborn',
    'opencv', 'nltk', 'spacy',

    # Cloud & DevOps 
    'aws', 'azure', 'google cloud', 'gcp', 'docker',
    'kubernetes', 'jenkins', 'ci/cd', 'terraform',
    'ansible', 'linux', 'nginx',

    # Version Control
    'git', 'github', 'gitlab', 'bitbucket',

    # Other Tools & Skills
    'rest api', 'graphql', 'microservices', 'agile', 'scrum',
    'jira', 'excel', 'power bi', 'tableau',
    'html', 'css', 'figma', 'photoshop',
    'android', 'ios', 'unity', 'wordpress',
    'networking', 'cybersecurity', 'ethical hacking',
    'autocad', 'solidworks',
    'accounting', 'tally', 'sap',
]


# ════════════════════════════════════════════════════════════
# PART 3 — FIELD EXTRACTORS
# ════════════════════════════════════════════════════════════

def extract_email(text):
    """Extract first email address found in the text."""
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    match   = re.search(pattern, text)
    return match.group(0) if match else ''


def extract_phone(text):
    """Extract first phone number found in the text."""
    pattern = r'(\+?[\d][\d\s\-().]{7,}[\d])'
    matches = re.findall(pattern, text)
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if 7 <= len(digits) <= 15:
            return m.strip()
    return ''


def extract_name(text):
    """
    Rule-based name extraction.
    The name is usually in the first few lines:
    - 2 to 5 words
    - Only letters, spaces, dots, hyphens
    - No email/phone/URL characters
    - Not a section header keyword
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    for line in lines[:8]:
        # Skip lines with special characters
        if re.search(r'[@\d/\\|#<>:;]', line):
            continue
        words = line.split()
        if len(words) < 2 or len(words) > 6:
            continue
        # Only letters, spaces, dots, hyphens
        if re.match(r'^[A-Za-z\s\.\-]+$', line):
            skip_words = [
                'resume', 'curriculum', 'vitae', 'cv', 'profile',
                'summary', 'objective', 'contact', 'address',
                'references', 'skills', 'education', 'experience',
            ]
            if not any(w in line.lower() for w in skip_words):
                return line.strip()

    return lines[0] if lines else ''


def extract_skills(text):
    """
    Match skills from SKILLS_LIST against the CV text.
    Uses word boundary regex to avoid partial matches.
    Returns list of matched skills in Title Case.
    """
    text_lower   = text.lower()
    found_skills = []

    for skill in SKILLS_LIST:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill.title())

    return found_skills


def extract_education(text):
    """
    Rule-based education extraction.
    Detects degree keywords and nearby institution names.
    Returns list of dicts.
    """
    education = []
    lines     = [l.strip() for l in text.split('\n')]

    degree_keywords = [
        'bachelor', 'master', 'phd', 'doctorate',
        'b.sc', 'b.tech', 'b.e', 'be', 'btech', 'bsc',
        'm.sc', 'm.tech', 'm.e', 'mtech', 'msc',
        'mba', 'bca', 'mca', 'diploma', 'b.a', 'm.a',
        'b.com', 'm.com', '+2', 'slc', 'high school',
        'secondary', 'higher secondary',
    ]

    institution_keywords = [
        'university', 'college', 'institute', 'school',
        'academy', 'polytechnic', 'campus',
    ]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        if any(deg in line_lower for deg in degree_keywords):
            # Extract graduation year
            year_match = re.search(r'(19|20)\d{2}', line)
            year       = int(year_match.group()) if year_match else None

            # Find institution in nearby lines
            institution  = ''
            search_range = lines[max(0, i - 2): i + 4]
            for nearby in search_range:
                if any(kw in nearby.lower() for kw in institution_keywords):
                    institution = nearby.strip()
                    break

            # Avoid duplicates
            already = any(e['degree'] == line.strip() for e in education)
            if not already and line.strip():
                education.append({
                    'degree':          line.strip(),
                    'institution':     institution,
                    'graduation_year': year,
                })

    return education


def extract_experience(text):
    """
    Rule-based experience extraction.
    Finds date ranges: 2018-2022, Jan 2020 - Mar 2022, 2021 - Present.
    Returns list of dicts.
    """
    experience   = []
    lines        = [l.strip() for l in text.split('\n')]

    date_pattern = re.compile(
        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]*)?\s*'
        r'((?:19|20)\d{2})'
        r'\s*[-–—to/]+\s*'
        r'((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,]*)?\s*'
        r'((?:19|20)\d{2}|present|current|now|till date|to date)',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        match = date_pattern.search(line)
        if not match:
            continue

        start_year = match.group(2)
        end_year   = match.group(4)

        # Find job title and company in nearby lines
        job_title = ''
        company   = ''

        for nearby in lines[max(0, i - 3): i + 2]:
            clean = nearby.strip()
            if not clean or date_pattern.search(clean):
                continue
            if not job_title:
                job_title = clean
            elif not company:
                company = clean

        # Collect description lines after the date line
        desc_lines = []
        for j in range(i + 1, min(i + 5, len(lines))):
            dl = lines[j].strip()
            if not dl:
                continue
            if date_pattern.search(dl):
                break
            desc_lines.append(dl)

        # Avoid duplicates
        already = any(
            e['start_date'] == start_year and e['job_title'] == job_title
            for e in experience
        )
        if not already:
            experience.append({
                'job_title':   job_title,
                'company':     company,
                'start_date':  start_year,
                'end_date':    end_year,
                'description': ' '.join(desc_lines),
            })

    return experience


# ════════════════════════════════════════════════════════════
# PART 4 — JOB TITLE PREDICTOR (rule-based)
# ════════════════════════════════════════════════════════════

def predict_job_title(skills):
    """
    Predict the most suitable job title based on matched skills.
    Returns (title, confidence_percentage).
    """
    skill_lower = [s.lower() for s in skills]

    rules = [
        {
            'title':    'Machine Learning Engineer',
            'keywords': ['machine learning', 'deep learning',
                         'tensorflow', 'pytorch', 'keras', 'nlp'],
            'min':      2,
        },
        {
            'title':    'Data Scientist',
            'keywords': ['python', 'pandas', 'numpy', 'scikit-learn',
                         'data science', 'matplotlib', 'r', 'data analysis'],
            'min':      3,
        },
        {
            'title':    'Full Stack Developer',
            'keywords': ['react', 'django', 'node.js', 'javascript',
                         'html', 'css', 'sql', 'rest api'],
            'min':      3,
        },
        {
            'title':    'Backend Developer',
            'keywords': ['django', 'flask', 'fastapi', 'postgresql',
                         'rest api', 'python', 'java', 'sql'],
            'min':      3,
        },
        {
            'title':    'Frontend Developer',
            'keywords': ['react', 'angular', 'vue', 'javascript',
                         'html', 'css', 'typescript', 'jquery'],
            'min':      3,
        },
        {
            'title':    'DevOps Engineer',
            'keywords': ['docker', 'kubernetes', 'aws', 'ci/cd',
                         'linux', 'jenkins', 'terraform', 'ansible'],
            'min':      2,
        },
        {
            'title':    'Android Developer',
            'keywords': ['android', 'kotlin', 'java', 'firebase'],
            'min':      2,
        },
        {
            'title':    'Cybersecurity Analyst',
            'keywords': ['cybersecurity', 'ethical hacking',
                         'networking', 'linux', 'python'],
            'min':      2,
        },
        {
            'title':    'Software Engineer',
            'keywords': ['python', 'java', 'c++', 'git', 'sql', 'agile'],
            'min':      2,
        },
    ]

    best_title      = 'Software Developer'
    best_confidence = 40
    best_matches    = 0

    for rule in rules:
        matches = sum(1 for kw in rule['keywords'] if kw in skill_lower)
        if matches >= rule['min'] and matches > best_matches:
            best_matches    = matches
            best_title      = rule['title']
            total           = len(rule['keywords'])
            best_confidence = min(98, int((matches / total) * 100) + 30)

    return best_title, best_confidence


# ════════════════════════════════════════════════════════════
# PART 5 — MAIN PARSE FUNCTION
# ════════════════════════════════════════════════════════════

def parse_resume(file_path):
    """
    Main entry point.
    Pass the full path to a PDF or TXT file.
    Returns a dict with all extracted fields.
    """
    if not os.path.exists(file_path):
        return {'success': False, 'message': 'File not found.'}

    # Step 1 — Extract raw text
    text = extract_text(file_path)

    if not text or len(text.strip()) < 20:
        return {
            'success': False,
            'message': 'Could not extract text from file. '
                       'Make sure the PDF is not image-only or scanned.'
        }

    # Step 2 — Run all extractors
    skills                      = extract_skills(text)
    predicted_title, confidence = predict_job_title(skills)

    return {
        'success':         True,
        'raw_text':        text,
        'name':            extract_name(text),
        'email':           extract_email(text),
        'phone':           extract_phone(text),
        'skills':          skills,
        'education':       extract_education(text),
        'experience':      extract_experience(text),
        'predicted_title': predicted_title,
        'confidence':      confidence,
    }