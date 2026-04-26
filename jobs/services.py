import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.dateparse import parse_date

from .models import Company, Job, JobCategory


SCRAPING_DIR = Path(__file__).resolve().parent / "scraping_scripts"
SCRAPER_OUTPUTS = {
    "merojob.py": ("merojob", "merojob_jobs.json"),
    "cedar_json.py": ("cedar", "cedar_extracted_jobs.json"),
    "proshore_json.py": ("proshore", "proshore_jobs.json"),
    "verisk_json.py": ("verisk", "verisk_extracted_jobs.json"),
}


def run_scrapers_and_sync_jobs() -> dict:
    summary = {"created": 0, "updated": 0, "failed": []}
    for script_name, (source, output_file) in SCRAPER_OUTPUTS.items():
        script_path = SCRAPING_DIR / script_name
        output_path = SCRAPING_DIR / output_file

        try:
            subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(SCRAPING_DIR),
                check=True,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except Exception as exc:  # noqa: BLE001
            summary["failed"].append({"source": source, "error": str(exc)})
            continue

        if not output_path.exists():
            summary["failed"].append({"source": source, "error": "Output JSON not found"})
            continue

        try:
            payload = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            summary["failed"].append({"source": source, "error": f"Invalid JSON: {exc}"})
            continue

        jobs = payload if isinstance(payload, list) else []
        for raw in jobs:
            changed = upsert_job(source=source, raw=raw)
            if changed == "created":
                summary["created"] += 1
            elif changed == "updated":
                summary["updated"] += 1

    return summary


def upsert_job(*, source: str, raw: dict) -> str | None:
    normalized = normalize_job_payload(source, raw)
    if not normalized["job_title"]:
        return None

    company, _ = Company.objects.get_or_create(
        companyName=normalized["company_name"] or "Unknown Company",
        defaults={
            "location": normalized["location"],
            "about": normalized["company_about"],
        },
    )
    company_changed = False
    if normalized["location"] and company.location != normalized["location"]:
        company.location = normalized["location"]
        company_changed = True
    if normalized["company_about"] and company.about != normalized["company_about"]:
        company.about = normalized["company_about"]
        company_changed = True
    if company_changed:
        company.save(update_fields=["location", "about"])

    category, _ = JobCategory.objects.get_or_create(
        categoryName=normalized["category"] or "General"
    )

    defaults = {
        "category": category,
        "company_id": company,
        "jobTitle": normalized["job_title"],
        "job_type": normalized["job_type"],
        "requiredSkill": normalized["required_skills"],
        "deadline": normalized["deadline"],
        "source_url": normalized["source_url"],
        "description": normalized["description"],
        "content_hash": normalized["content_hash"],
    }

    lookup = {
        "source": source,
        "source_job_id": normalized["source_job_id"],
    }
    try:
        with transaction.atomic():
            job, created = Job.objects.get_or_create(**lookup, defaults=defaults)
    except IntegrityError:
        job = Job.objects.filter(**lookup).first()
        created = False

    if created:
        return "created"

    if not job:
        return None

    if job.content_hash != normalized["content_hash"]:
        for key, value in defaults.items():
            setattr(job, key, value)
        job.save()
        return "updated"

    return None


def get_recommended_jobs_for_prediction(predicted_title: str):
    if not predicted_title:
        return Job.objects.none()

    base_query = (
        Q(jobTitle__icontains=predicted_title)
        | Q(category__categoryName__iexact=predicted_title)
        | Q(category__categoryName__icontains=predicted_title)
    )
    tokens = [token.strip() for token in predicted_title.lower().split() if len(token.strip()) > 2]
    token_query = Q()
    for token in tokens:
        token_query |= Q(jobTitle__icontains=token)
        token_query |= Q(category__categoryName__icontains=token)
        token_query |= Q(requiredSkill__icontains=token)
        token_query |= Q(description__icontains=token)

    return Job.objects.select_related("company_id", "category").filter(base_query | token_query).distinct()


def build_match_reasons(job: Job, predicted_title: str) -> list[str]:
    reasons: list[str] = []
    predicted = (predicted_title or "").strip().lower()
    if not predicted:
        return reasons

    job_title = (job.jobTitle or "").lower()
    category = (job.category.categoryName or "").lower() if job.category else ""
    skills = (job.requiredSkill or "").lower()
    description = (job.description or "").lower()

    if predicted in job_title:
        reasons.append("Job title contains your predicted role.")
    if predicted == category:
        reasons.append("Job category exactly matches your predicted role.")
    elif predicted in category:
        reasons.append("Job category is similar to your predicted role.")
    if predicted in skills:
        reasons.append("Required skills mention your predicted role.")
    if predicted in description:
        reasons.append("Job description aligns with your predicted role.")

    if not reasons:
        reasons.append("Matched using fuzzy title/category similarity.")
    return reasons


def normalize_job_payload(source: str, raw: dict) -> dict:
    title = (raw.get("title") or "").strip()
    company_name = (
        raw.get("company")
        or raw.get("company ")
        or raw.get("client_name")
        or "Unknown Company"
    )
    skills = raw.get("skills") or raw.get("job qualification") or raw.get("qualifications") or ""
    description = (
        raw.get("job_description")
        or raw.get("description")
        or raw.get("Job Summary")
        or raw.get("job description")
        or ""
    )
    responsibilities = raw.get("job responsibilities") or raw.get("roles") or ""
    category = raw.get("category") or ""

    source_job_id = (
        str(raw.get("job_id") or raw.get("id") or raw.get("itemId") or "").strip()
    )
    source_url = (raw.get("url") or "").strip()
    if not source_job_id:
        source_job_id = hashlib.sha256(
            f"{source}:{title}:{company_name}".encode("utf-8")
        ).hexdigest()[:32]

    merged_text = " ".join(
        [
            title,
            company_name,
            str(skills),
            str(description),
            str(responsibilities),
            str(raw.get("deadline") or ""),
            str(raw.get("employment_type") or raw.get("requition type") or ""),
        ]
    ).strip()
    content_hash = hashlib.sha256(merged_text.encode("utf-8")).hexdigest()

    return {
        "job_title": title,
        "company_name": str(company_name).strip(),
        "location": str(raw.get("location") or "").strip(),
        "company_about": str(raw.get("company_description") or raw.get("about") or "").strip(),
        "job_type": str(raw.get("employment_type") or raw.get("workplace_type") or raw.get("requition type") or "N/A")[:15],
        "required_skills": str(skills).strip(),
        "description": f"{description}\n{responsibilities}".strip(),
        "deadline": parse_possible_date(raw.get("deadline") or raw.get("posted_date")),
        "category": str(category).strip() or infer_category_from_title(title),
        "source_url": source_url,
        "source_job_id": source_job_id,
        "content_hash": content_hash,
    }


def infer_category_from_title(job_title: str) -> str:
    title = job_title.lower()
    if "data" in title:
        return "Data"
    if "engineer" in title or "developer" in title:
        return "Software Engineer"
    if "design" in title:
        return "Designer"
    if "manager" in title:
        return "Management"
    return "General"


def parse_possible_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    parsed = parse_date(str(value)[:10])
    return parsed
