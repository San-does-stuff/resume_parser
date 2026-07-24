from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import re
import random

BASE_URL = "https://proshore.eu/careers/#talent-pool"


def setup_driver():
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()))


def get_current_job_openings(driver, wait):
    driver.get(BASE_URL)

    job_opening_container = wait.until(
        EC.presence_of_all_elements_located(
            (By.CLASS_NAME, "homerun-widget__list-item")
        )
    )

    job_links = []

    for links in job_opening_container:
        anchor = links.find_element(By.TAG_NAME, "a")
        text = anchor.text.strip()

        idx = text.lower().find("kathmandu")
        if idx != -1:
            title = text[:idx].strip()
            location = text[idx:].strip()
        else:
            title = text
            location = ""

        job_links.append({
            "title_text": title,
            "location": location,
            "url": anchor.get_attribute("href")
        })

    return job_links


def simple_split(text):
    markers = [
        "What you will be doing",
        "What we offer you",
        "Necessary Skills",
        "Necessary Technical Skills",
        "Our selection process",
        "Deadline for Job Application:"
    ]

    positions = []
    lower_text = text.lower()

    for marker in markers:
        pos = lower_text.find(marker.lower())
        if pos != -1:
            positions.append((pos, marker))

    positions.sort()

    sections = {}
    for i, (pos, marker) in enumerate(positions):
        start = pos + len(marker)
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)

        content = text[start:end].strip()
        content = re.sub(r"\n+", " ", content)

        sections[marker] = content

    return sections


def scrape_each_opening(driver, wait, job_links):
    cleaned_jobs = []

    for links in job_links:
        driver.get(links["url"])

        job_location = links["location"]
        job_title = links["title_text"]

        try:
            intro_text = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "intro-text"))
            ).text
        except:
            intro_text = ""

        try:
            job_hours = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "about"))
            ).text
        except:
            job_hours = ""

        try:
            descriptive_block = wait.until(
                EC.presence_of_element_located((By.ID, "block-5"))
            )
            full_text = descriptive_block.text
            sections = simple_split(full_text)
        except:
            sections = {}

        summary = sections.get("What you will be doing", "")
        qualifications = sections.get("Necessary Skills") or sections.get("Necessary Technical Skills", "")
        environment = sections.get("What we offer you", "")
        deadline = sections.get("Deadline for Job Application:", "")

        cleaned_jobs.append(
            {
                "company ": "Proshore",
                # "itemId": random.randint(0, 10000),
                "location": job_location,
                "title": job_title,
                "Job Summary": intro_text,
                "Job Hours": job_hours,
                "roles": summary,
                "qualifications": qualifications,
                "environment": environment,
                "about": intro_text,
                # "deadline": deadline
            }
        )

    return cleaned_jobs


def save_data(all_jobs_data):
    with open("proshore_jobs.json", "w", encoding="utf-8") as f:
        json.dump(all_jobs_data, f, indent=4, ensure_ascii=False)

    print("\n Proshore's Site Scraping completed. Data saved to jobs.json")


def main():
    driver = setup_driver()
    wait = WebDriverWait(driver, 6)

    job_links = get_current_job_openings(driver, wait)
    jobs = scrape_each_opening(driver, wait, job_links)

    save_data(jobs)
    driver.quit()


if __name__ == "__main__":
    main()