"""
merojob_scrape.py

Fetches job listings from the merojob API and writes them straight into
the database. No intermediate JSON file, no Django management command --
just run this file directly:

    python merojob_scrape.py

This file needs to live in the same folder as manage.py (your Django
project root), since it needs to load your Django settings to use the
models.
"""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime

import django
import httpx
from bs4 import BeautifulSoup

# --- Set up Django BEFORE importing any models --------------------------
# This is the one thing a plain script needs that a management command
# gets for free: telling Django which settings module to use, and
# initializing it, before we're allowed to import/use any models.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resume_parser.settings")
django.setup()

from jobs.models import Job, JobCategory, Company
from jobs.category_matcher import match_category

try:
    from resume.services.pdf_parser import SKILLS_LIST
except ImportError:
    # If the resume app's skill list isn't importable for some reason,
    # fall back to an empty list rather than crashing the whole sync --
    # skills will just come from the scraper's own "skills" field only.
    SKILLS_LIST = []


# BASE_URL = "https://api.merojob.com/api/v1/jobs/?page=10&page_size=1&limit=6&offset=1"
BASE_URL = "https://api.merojob.com/api/v1/jobs/?page=1&page_size=6&categories=IT%20%26%20Telecommunication"
SOURCE_NAME = "merojob"


def clean_html(html_text):
    """Convert HTML to clean text."""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


async def fetch_jobs():
    """Fetch every page of job listings from the merojob API."""
    url = BASE_URL
    all_jobs = []

    async with httpx.AsyncClient(timeout=10) as client:
        while url:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

                for job in data.get("results", []):
                    client_info = job.get("client", {}) or {}
                    salary_info = job.get("offered_salary", {}) or {}

                    job_data = {
                        "id": job.get("id"),
                        "title": job.get("title"),
                        "company": client_info.get("client_name"),
                        "location": client_info.get("location"),
                        "job_link": "https://merojobs.com/" + str(job.get("slug")),
                        "job_description": clean_html(job.get("description")),
                        "job_specification": clean_html(job.get("specification")),
                        "company_description": clean_html(client_info.get("about")),
                        "skills": job.get("skills"),
                        "job_level": job.get("job_level"),
                        "employment_type": job.get("available_for"),
                        "salary": salary_info.get("minimum"),
                        "deadline": job.get("deadline"),
                    }
                    print(job_data["job_link"])
                    all_jobs.append(job_data)


                url = data.get("next")

            except httpx.HTTPError as error:
                print(f"Error while fetching jobs: {error}")
                break

    return all_jobs


# --- Everything below here talks to the database -------------------------

def get_or_create_company(name, location, about):
    name = (name or "Unknown Company").strip()

    company, _ = Company.objects.get_or_create(companyName=name)

    # Fill in location/about if we didn't have them before, without
    # overwriting anything that's already there.
    needs_save = False
    if location and not company.location:
        company.location = location
        needs_save = True
    if about and not company.about:
        company.about = about
        needs_save = True

    if needs_save:
        company.save(update_fields=["location", "about"])

    return company


def extract_skills_from_text(text):
    if not text or not SKILLS_LIST:
        return []

    normalized_text = re.sub(r"[^a-z0-9+#.\- ]+", " ", text.lower())

    found = []
    seen = set()
    for skill in SKILLS_LIST:
        if re.search(r"\b" + re.escape(skill) + r"\b", normalized_text):
            if skill not in seen:
                seen.add(skill)
                found.append(skill)

    return found


def get_skills(job_dict, title):
    scraped_skills = job_dict.get("skills") or []

    if scraped_skills:
        cleaned = []
        for skill in scraped_skills:
            skill = str(skill).strip().lower()
            if skill:
                cleaned.append(skill)
        return cleaned

    # No skills came from the scraper -- try to pull some out of the
    # title/description/specification text ourselves.
    combined_text = " ".join([
        title,
        job_dict.get("job_description", "") or "",
        job_dict.get("job_specification", "") or "",
    ])
    return extract_skills_from_text(combined_text)


def build_job_type(employment_type_list):
    if not employment_type_list:
        return ""

    first_type = str(employment_type_list[0])
    # job_type is a 15-character field, so trim anything longer.
    return first_type[:15]


def parse_deadline(raw_value):
    if not raw_value:
        return None

    try:
        # Scraped dates look like "2026-07-28T18:10:00Z". Python's
        # datetime.fromisoformat doesn't understand the trailing "Z" on
        # its own, so swap it for "+00:00" first.
        cleaned_value = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned_value).date()
    except (ValueError, TypeError):
        return None


def build_content_hash(job_dict, skills_list):
    # A fingerprint of everything that would count as a "real change" to
    # this job listing. If none of these fields changed since the last
    # sync, we skip re-writing the row.
    payload = {
        "title": job_dict.get("title", ""),
        "description": job_dict.get("job_description", ""),
        "specification": job_dict.get("job_specification", ""),
        "deadline": job_dict.get("deadline", ""),
        "salary": job_dict.get("salary", 0),
        "skills": sorted(skills_list),
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def save_jobs_to_database(jobs_data):
    created_count = 0
    updated_count = 0
    unchanged_count = 0
    skipped_count = 0

    for job_dict in jobs_data:
        source_job_id = str(job_dict.get("id", "")).strip()
        title = (job_dict.get("title") or "").strip()

        if not source_job_id or not title:
            skipped_count += 1
            continue

        company = get_or_create_company(
            job_dict.get("company"),
            job_dict.get("location"),
            job_dict.get("company_description"),
        )

        category_name = match_category(title)
        category, _ = JobCategory.objects.get_or_create(categoryName=category_name)

        skills_list = get_skills(job_dict, title)
        content_hash = build_content_hash(job_dict, skills_list)

        existing_job = Job.objects.filter(
            source=SOURCE_NAME,
            source_job_id=source_job_id,
        ).first()

        if existing_job and existing_job.content_hash == content_hash:
            unchanged_count += 1
            continue

        defaults = {
            "category": category,
            "company_id": company,
            "jobTitle": title,
            "job_type": build_job_type(job_dict.get("employment_type")),
            "requiredSkill": ", ".join(skills_list),
            "salary": job_dict.get("salary") or 0.0,
            "deadline": parse_deadline(job_dict.get("deadline")),
            "source_url": job_dict.get("job_link", "") or "",
            "description": job_dict.get("job_description", "") or "",
            "content_hash": content_hash,
        }

        job_obj, was_created = Job.objects.update_or_create(
            source=SOURCE_NAME,
            source_job_id=source_job_id,
            defaults=defaults,
        )

        if was_created:
            created_count += 1
        else:
            updated_count += 1

    print(
        "Done. "
        f"Created: {created_count}, "
        f"Updated: {updated_count}, "
        f"Unchanged: {unchanged_count}, "
        f"Skipped (missing id/title): {skipped_count}"
        
    )


async def main():
    jobs = await fetch_jobs()
    print(f"✅ Fetched {len(jobs)} jobs from merojob")
    return jobs


if __name__ == "__main__":
    # Run the async fetch to completion first. Once asyncio.run() returns,
    # the event loop is fully closed -- only then is it safe to make
    # normal (synchronous) Django ORM calls. Calling ORM methods while an
    # event loop is still running raises SynchronousOnlyOperation, even if
    # nothing else is happening concurrently at that moment.
    fetched_jobs = asyncio.run(main())
    save_jobs_to_database(fetched_jobs)