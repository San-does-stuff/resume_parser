import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils.dateparse import parse_date

from .models import Company, Job, JobCategory
from .category_matcher import match_category


SCRAPING_DIR = Path(__file__).resolve().parent / "scraping_scripts"
SCRAPER_OUTPUTS = {
    "merojob.py": ("merojob", "merojob_jobs.json"),
    "cedar_json.py": ("cedar", "cedar_extracted_jobs.json"),
    "proshore_json.py": ("proshore", "proshore_jobs.json"),
    "verisk_json.py": ("verisk", "verisk_extracted_jobs.json"),
}

# Common words that show up in almost every tech job title/description
# and therefore shouldn't count as a meaningful signal on their own (e.g.
# "developer" or "engineer" appearing ANYWHERE shouldn't be enough to call
# something a match -- nearly every listing on a tech job board has one
# of these words somewhere).
GENERIC_TITLE_WORDS = {
    "developer", "engineer", "engineering", "specialist", "officer",
    "executive", "analyst", "associate", "senior", "junior", "lead",
    "manager", "assistant", "consultant", "intern", "coordinator",
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


def _tokenize(text: str) -> set[str]:
    """Turn text into a set of lowercase, meaningful words (3+ letters)."""
    if not text:
        return set()
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {word for word in words if len(word) > 2}


def _score_job_match(job: Job, predicted_lower: str, predicted_tokens: set[str]) -> float:
    """
    Score how well a job matches the predicted job category, from 0 up.
    Higher = stronger match. This replaces "does any single word appear
    anywhere" with "how much do these two things actually have in
    common", so a job doesn't get recommended just because it contains
    one very common word like 'developer' or 'engineer'.
    """
    job_title = (job.jobTitle or "").lower()
    category = (job.category.categoryName or "").lower() if job.category else ""
    skills = (job.requiredSkill or "").lower()
    description = (job.description or "").lower()

    score = 0.0

    # Category match is the strongest possible signal -- it means our
    # category-matching step already decided this job belongs to
    # (roughly) the same role as the resume's predicted category.
    if predicted_lower and category:
        if predicted_lower == category:
            score += 5.0
        elif predicted_lower in category or category in predicted_lower:
            score += 3.0

    # The full predicted phrase appearing in the job title is also a
    # strong, specific signal (e.g. "full stack developer" appearing as
    # a whole phrase, not just the word "developer" on its own).
    if predicted_lower and predicted_lower in job_title:
        score += 4.0

    # Beyond that, count MEANINGFUL shared words, but don't give credit
    # for generic words every tech job has anyway.
    job_title_tokens = _tokenize(job_title) - GENERIC_TITLE_WORDS
    meaningful_predicted_tokens = predicted_tokens - GENERIC_TITLE_WORDS

    shared_title_words = meaningful_predicted_tokens & job_title_tokens
    score += len(shared_title_words) * 1.5

    skills_tokens = _tokenize(skills)
    shared_skill_words = meaningful_predicted_tokens & skills_tokens
    score += len(shared_skill_words) * 0.75

    description_tokens = _tokenize(description)
    shared_description_words = meaningful_predicted_tokens & description_tokens
    score += len(shared_description_words) * 0.25

    return score


# A job needs at least this much score to be considered a real
# recommendation, not just an incidental word overlap somewhere.
MIN_MATCH_SCORE = 3.0

# Don't return an unbounded number of "recommended" jobs.
MAX_RECOMMENDATIONS = 30


def get_recommended_jobs_for_prediction(predicted_title: str):
    if not predicted_title:
        return Job.objects.none()

    predicted_lower = predicted_title.strip().lower()
    predicted_tokens = _tokenize(predicted_lower)

    # Cast a reasonably wide net at the database level first (this can
    # still include weak/irrelevant matches -- that's fine, we score and
    # filter properly in Python next).
    base_query = (
        Q(jobTitle__icontains=predicted_lower)
        | Q(category__categoryName__iexact=predicted_lower)
        | Q(category__categoryName__icontains=predicted_lower)
    )
    for token in predicted_tokens:
        base_query |= Q(jobTitle__icontains=token)
        base_query |= Q(category__categoryName__icontains=token)

    candidates = Job.objects.select_related("company_id", "category").filter(base_query).distinct()

    scored_jobs = []
    for job in candidates:
        score = _score_job_match(job, predicted_lower, predicted_tokens)
        if score >= MIN_MATCH_SCORE:
            scored_jobs.append((score, job))

    scored_jobs.sort(key=lambda pair: pair[0], reverse=True)

    return [job for _score, job in scored_jobs[:MAX_RECOMMENDATIONS]]


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
        predicted_tokens = _tokenize(predicted) - GENERIC_TITLE_WORDS
        job_title_tokens = _tokenize(job_title) - GENERIC_TITLE_WORDS
        shared_words = predicted_tokens & job_title_tokens
        if shared_words:
            words_list = ", ".join(sorted(shared_words))
            reasons.append(f"Shares key words with your predicted role: {words_list}.")
        else:
            reasons.append("Matched using overall similarity to your predicted role.")

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
        "category": str(category).strip() or match_category(title),
        "source_url": source_url,
        "source_job_id": source_job_id,
        "content_hash": content_hash,
    }


def parse_possible_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    parsed = parse_date(str(value)[:10])
    return parsed