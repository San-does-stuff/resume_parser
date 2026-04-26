import argparse
import csv
import json
import re
from pathlib import Path


BASE_DATASET_PATH = Path("datasets/structured_resume_dataset.csv")
OUTPUT_DATASET_PATH = Path("datasets/structured_resume_dataset.enhanced.csv")
SCRAPING_DIR = Path("jobs/scraping_scripts")
SCRAPED_JSON_FILES = [
    SCRAPING_DIR / "merojob_jobs.json",
    SCRAPING_DIR / "cedar_extracted_jobs.json",
    SCRAPING_DIR / "proshore_jobs.json",
    SCRAPING_DIR / "verisk_extracted_jobs.json",
]


IT_RESUME_SEEDS = [
    {
        "job_category": "Testing",
        "resume_text": "QA engineer with 4 years of manual and automation testing experience in web applications. Built regression suites using Selenium and Pytest, tracked defects in Jira, and improved release quality.",
        "skills": "qa, testing, selenium, pytest, jira, api testing, regression testing",
        "education": "BSc Computer Science",
        "experience": "QA Engineer",
    },
    {
        "job_category": "Project Manager",
        "resume_text": "IT project manager experienced in Agile delivery, stakeholder communication, sprint planning, and risk mitigation. Led multi-team SaaS projects and delivered releases on schedule.",
        "skills": "project management, agile, scrum, jira, stakeholder management, risk management",
        "education": "MBA, BSc Information Systems",
        "experience": "Project Manager",
    },
    {
        "job_category": "DevOps Engineer",
        "resume_text": "DevOps engineer with hands-on CI/CD pipelines, Docker, Kubernetes, Terraform, and AWS. Improved deployment frequency and reduced rollback incidents using infrastructure automation.",
        "skills": "devops, docker, kubernetes, terraform, aws, ci/cd, linux",
        "education": "BSc Software Engineering",
        "experience": "DevOps Engineer",
    },
    {
        "job_category": "Data Science",
        "resume_text": "Data scientist focused on predictive modeling, NLP, and experimentation. Built classification models in Python using pandas and scikit-learn and presented insights through dashboards.",
        "skills": "python, machine learning, data science, pandas, numpy, scikit-learn, nlp",
        "education": "MSc Data Science",
        "experience": "Data Scientist",
    },
    {
        "job_category": "Java Developer",
        "resume_text": "Backend Java developer experienced in Spring Boot microservices, REST APIs, PostgreSQL, and message queues. Optimized performance and improved API reliability in production.",
        "skills": "java, spring boot, rest api, microservices, postgresql, kafka",
        "education": "BE Computer Engineering",
        "experience": "Java Developer",
    },
    {
        "job_category": "Web Designing",
        "resume_text": "Frontend developer and UI designer with React, JavaScript, HTML, CSS, and responsive design expertise. Collaborated with product teams to deliver intuitive interfaces.",
        "skills": "react, javascript, html, css, figma, responsive design, ui/ux",
        "education": "BSc Multimedia and Design",
        "experience": "Frontend Developer",
    },
    {
        "job_category": "Network Security Engineer",
        "resume_text": "Security engineer with SOC monitoring, SIEM alerting, vulnerability management, and incident response experience. Hardened cloud and network systems for enterprise clients.",
        "skills": "cybersecurity, soc, siem, network security, incident response, vulnerability management",
        "education": "BSc Information Security",
        "experience": "Security Engineer",
    },
    {
        "job_category": "Business Analyst",
        "resume_text": "Business analyst with strong requirement gathering, process mapping, and data-driven decision support. Worked with engineering and product teams to define implementation scope.",
        "skills": "business analysis, requirements gathering, process mapping, sql, stakeholder communication",
        "education": "BBA Information Management",
        "experience": "Business Analyst",
    },
]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def load_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def load_scraped_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for json_path in SCRAPED_JSON_FILES:
        if not json_path.exists():
            continue
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(payload, list):
            continue

        for item in payload:
            title = normalize_space(str(item.get("title") or ""))
            if not title:
                continue
            category = derive_category(title, item)
            description = normalize_space(
                " ".join(
                    [
                        str(item.get("job_description") or ""),
                        str(item.get("description") or ""),
                        str(item.get("Job Summary") or ""),
                        str(item.get("job description") or ""),
                        str(item.get("job responsibilities") or item.get("roles") or ""),
                    ]
                )
            )
            skills = normalize_space(
                str(item.get("skills") or item.get("job qualification") or item.get("qualifications") or "")
            )
            education = "Bachelors in Computer Science or related field"
            experience = title
            resume_text = normalize_space(
                f"{title} professional with strong IT experience. {description} Skilled in {skills}."
            )
            if len(resume_text.split()) < 12:
                continue
            rows.append(
                {
                    "job_category": category,
                    "resume_text": resume_text,
                    "skills": skills,
                    "education": education,
                    "experience": experience,
                    "email": "",
                    "phone": "",
                }
            )
    return rows


def derive_category(title: str, item: dict) -> str:
    title_l = title.lower()
    category = normalize_space(str(item.get("category") or ""))
    if category:
        return category
    if "qa" in title_l or "test" in title_l:
        return "Testing"
    if "project manager" in title_l or "program manager" in title_l:
        return "Project Manager"
    if "java" in title_l:
        return "Java Developer"
    if "sql" in title_l:
        return "SQL Developer"
    if "data" in title_l or "ml" in title_l:
        return "Data Science"
    if "security" in title_l:
        return "Network Security Engineer"
    if "dotnet" in title_l or ".net" in title_l:
        return "DotNet Developer"
    if "frontend" in title_l or "ui" in title_l or "ux" in title_l or "web" in title_l:
        return "Web Designing"
    if "business analyst" in title_l:
        return "Business Analyst"
    if "devops" in title_l:
        return "DevOps Engineer"
    if "sap" in title_l:
        return "SAP Developer"
    if "etl" in title_l:
        return "ETL Developer"
    return "Software Engineer"


def seed_rows_to_dataset_shape() -> list[dict[str, str]]:
    rows = []
    for seed in IT_RESUME_SEEDS:
        row = dict(seed)
        row["email"] = ""
        row["phone"] = ""
        rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fill_missing_fields(row: dict[str, str], fieldnames: list[str]) -> dict[str, str]:
    normalized = {k: row.get(k, "") for k in fieldnames}
    normalized["text_length"] = str(len(normalized.get("resume_text", "").split()))
    skill_tokens = [token.strip() for token in normalized.get("skills", "").split(",") if token.strip()]
    normalized["skills_count"] = str(len(skill_tokens))
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Augment resume dataset with scraped IT jobs and curated IT seed resumes.")
    parser.add_argument("--base-path", default=str(BASE_DATASET_PATH))
    parser.add_argument("--output-path", default=str(OUTPUT_DATASET_PATH))
    args = parser.parse_args()

    base_rows, fieldnames = load_csv_rows(Path(args.base_path))
    if not fieldnames:
        raise ValueError("Base dataset has no headers.")

    new_rows = load_scraped_rows() + seed_rows_to_dataset_shape()
    enhanced_rows = list(base_rows)
    for row in new_rows:
        enhanced_rows.append(fill_missing_fields(row, fieldnames))

    write_rows(Path(args.output_path), enhanced_rows, fieldnames)
    print(f"Base rows: {len(base_rows)}")
    print(f"Added rows: {len(new_rows)}")
    print(f"Enhanced rows: {len(enhanced_rows)}")
    print(f"Wrote: {args.output_path}")


if __name__ == "__main__":
    main()
