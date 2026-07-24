import re


STOPWORDS = {"and", "of", "in", "the", "a", "for", "to", "with", "on"}

# Sets the minimum similarity required for a scraped job title to match a known category
# otherwise, it is marked as "Uncategorized."
MIN_MATCH_SCORE = 0.15

# 151 job titles used to train the resume classifier.
CATEGORY_TITLES = [
    ".NET Developer", "AI Engineer", "AI Research Intern", "AI/ML Engineer",
    "AI/ML Intern", "API Documentation Specialist", "AR/VR Developer",
    "AWS Engineer", "Agile Coach", "Android Developer", "Angular Developer",
    "Associate Product Manager", "Associate Software Engineer",
    "Automation Test Engineer", "Azure Engineer", "Backend Developer",
    "Backend Intern", "Blockchain Developer", "Business Analyst",
    "Business Intelligence (BI) Analyst", "CMS Developer", "CRM Specialist",
    "CTO (Chief Technology Officer)", "Cloud Administrator", "Cloud Engineer",
    "Computer Vision Engineer", "Cybersecurity Analyst", "Cybersecurity Intern",
    "Data Analyst", "Data Engineer", "Data Science Intern", "Data Scientist",
    "Database Administrator (DBA)", "Database Developer",
    "Desktop Support Engineer", "DevOps Engineer", "DevOps Intern",
    "Digital Forensics Analyst", "Digital Marketing Executive",
    "Django Developer", "Documentation Engineer", "Dynamics 365 Developer",
    "ERP Consultant", "Engineering Manager", "Enterprise Architect",
    "Ethical Hacker", "Flutter Developer", "Flutter Intern",
    "Frontend Developer", "Frontend Intern", "Full Stack Developer",
    "GRC Analyst", "Game Developer", "Generative AI Engineer",
    "Google Cloud Engineer", "Graphic Designer", "Help Desk Engineer",
    "IT Administrator", "IT Consultant", "IT Executive", "IT Manager",
    "IT Officer", "IT Support Intern", "IT Support Officer",
    "Incident Response Analyst", "Information Security Analyst",
    "Infrastructure Engineer", "Infrastructure Support Engineer",
    "IoT Developer", "Java Developer", "Junior Software Developer",
    "Kubernetes Engineer", "Laravel Developer", "Linux System Administrator",
    "MLOps Engineer", "Machine Learning Engineer", "Magento Developer",
    "Manual QA Engineer", "Marketing Automation Specialist",
    "Mobile App Developer", "Motion Designer", "NLP Engineer",
    "Network Administrator", "Network Engineer", "Network Intern",
    "Node.js Developer", "Odoo Developer", "Oracle DBA", "PHP Developer",
    "Penetration Tester", "Performance Test Engineer", "Platform Engineer",
    "PostgreSQL Developer", "Product Designer", "Product Manager",
    "Product Owner", "Project Manager", "Prompt Engineer", "Python Developer",
    "Python Intern", "QA Analyst", "QA Engineer", "QA Intern",
    "React Developer", "React Intern", "React Native Developer",
    "Research Engineer", "Robotics Engineer", "SAP Consultant",
    "SDET (Software Development Engineer in Test)", "SEO Specialist",
    "SOC Analyst", "SQL Developer", "Salesforce Administrator",
    "Salesforce Developer", "Scrum Master", "Security Consultant",
    "Security Engineer", "Server Administrator", "Shopify Developer",
    "Site Reliability Engineer (SRE)", "Smart Contract Developer",
    "Software Architect", "Software Developer", "Software Engineer",
    "Software Engineering Intern", "Software Test Engineer",
    "Solutions Architect", "System Administrator", "Team Lead",
    "Technical Lead", "Technical Product Manager", "Technical Project Manager",
    "Technical Support Engineer", "Technical Writer", "Technology Consultant",
    "UI Designer", "UI/UX Designer", "UI/UX Intern", "UX Designer",
    "Vue.js Developer", "Vulnerability Assessment and Penetration Tester (VAPT)",
    "Web Analyst", "Web Developer", "Web3 Developer", "WordPress Developer",
    "iOS Developer",
]


def tokenize_title(text):
    """turn a job title into a set of lowercase, meaningful words"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    tokens = set()
    for word in text.split():
        if word in STOPWORDS:
            continue
        if len(word) < 2:
            continue
        tokens.add(word)

    return tokens


# Stores the processed names of all known job categories in advance so they can be matched more quickly later
_CATEGORY_TOKENS = {}
for _title in CATEGORY_TITLES:
    _CATEGORY_TOKENS[_title] = tokenize_title(_title)


def match_category(job_title):
    """
    Compares the scraped job title with known job categories
    and returns the closest match, or "Uncategorized" if no good match is found
    """
    if not job_title:
        return "Uncategorized"

    job_tokens = tokenize_title(job_title)
    if not job_tokens:
        return "Uncategorized"

    best_title = None
    best_score = 0.0

    for title, category_tokens in _CATEGORY_TOKENS.items():
        if not category_tokens:
            continue

        shared_words = job_tokens & category_tokens
        if not shared_words:
            continue

        all_words = job_tokens | category_tokens
        score = len(shared_words) / len(all_words)

        if score > best_score:
            best_score = score
            best_title = title

    if best_title is None or best_score < MIN_MATCH_SCORE:
        return "Uncategorized"

    return best_title