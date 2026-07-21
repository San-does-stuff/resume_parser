import httpx
import asyncio
import json
from bs4 import BeautifulSoup

BASE_URL = "https://api.merojob.com/api/v1/jobs/?page=1&page_size=1&limit=6&offset=1"


def clean_html(html_text):
    """Convert HTML to clean text"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    return soup.get_text(separator=" ", strip=True)


async def fetch_jobs():
    url = BASE_URL
    all_jobs = []

    async with httpx.AsyncClient(timeout=10) as client:
        while url:
            try:
                res = await client.get(url)
                res.raise_for_status()
                data = res.json()

                for job in data.get("results", []):
                    job_data = {
                        "id": job.get("id"),
                        "title": job.get("title"),
                        "company": job.get("client", {}).get("client_name"),
                        "location": job.get("client", {}).get("location"),

                        "job_description": clean_html(job.get("description")),
                        "job_specification": clean_html(job.get("specification")),
                        "company_description": clean_html(
                            job.get("client", {}).get("about")
                        ),

                        "skills": job.get("skills"),
                        "job_level": job.get("job_level"),
                        "employment_type": job.get("available_for"),
                        "salary": job.get("offered_salary", {}).get("minimum"),
                        "deadline": job.get("deadline"),
                    }

                    all_jobs.append(job_data)

                url = data.get("next")

            except httpx.HTTPError as e:
                print(f"Error: {e}")
                break

    return all_jobs


async def main():
    jobs = await fetch_jobs()

    with open("merojob_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=4)

    print(f"✅ Saved {len(jobs)} jobs to merojob_jobs.json")


# run
asyncio.run(main())