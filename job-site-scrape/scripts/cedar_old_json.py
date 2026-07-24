import requests
from html import unescape
import re
import json

def simple_split(text):
    """Simple split with basic cleaning"""
    
    # Define section markers
    markers = [
        "Position Summary",
        "Roles & Responsibilities",
        "Required Experience / Qualifications",
        "Your Future Working Environment", 
        "About Cedar Gate",
        "Deadline for Job Application:"
    ]
    
    # Find positions of each marker
    positions = []
    for marker in markers:
        pos = text.find(marker)
        if pos != -1:
            positions.append((pos, marker))
    
    # Sort by position
    positions.sort()
    
    # Extract sections
    sections = {}
    for i, (pos, marker) in enumerate(positions):
        start = pos + len(marker)
        end = positions[i+1][0] if i+1 < len(positions) else len(text)
        content = text[start:end].strip()
        sections[marker] = content
    
    return sections

# CedarGate's Job list api
url = "https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions?cid=00938235-a9f7-41c8-88da-16d4f27e21c1&timeStamp=1771496441022&ccId=9200975014487_2&lang=en_US&ccId=9200975014487_2&locale=en_US&$top=10"

response = requests.get(url)

response_data = response.json()
surface_job_data = response_data.get("jobRequisitions")

cleaned_jobs = []


for i in range(0,len(surface_job_data)):
    itemId = surface_job_data[i].get("itemID")
    title = surface_job_data[i].get("requisitionTitle")
    posted_date = surface_job_data[i].get("postDate")
    company_name = "Cedar Gate"
    # location = surface_job_data
    page_id = surface_job_data[i].get("customFieldGroup").get("stringFields")[0].get("stringValue")

    second_page_url = f"https://workforcenow.adp.com/mascsr/default/careercenter/public/events/staffing/v1/job-requisitions/{page_id}?cid=00938235-a9f7-41c8-88da-16d4f27e21c1&timeStamp=1771499289299&ccId=9200975014487_2&lang=en_US&ccId=9200975014487_2&locale=en_US"
    page = requests.get(second_page_url)
    data = page.json()
    job_requisition_data = data.get("requisitionDescription")

    # cleaning description
    job_requisition_data = unescape(job_requisition_data)
    job_requisition_data = re.sub(r'\s+', ' ', job_requisition_data)
    job_requisition_data = re.sub(r'<[^>]+>', '', job_requisition_data).strip()

    sections = simple_split(job_requisition_data)

    # Access each section
    summary = sections.get("Position Summary", "")
    roles = sections.get("Roles & Responsibilities", "")
    qualifications = sections.get("Required Experience / Qualifications", "")
    environment = sections.get("Your Future Working Environment", "")
    about = sections.get("About Cedar Gate", "")
    deadline = sections.get("Deadline for Job Application:", "")

    cleaned_jobs.append(
        {
            "company ":company_name,
            "itemId" : itemId,
            "title" : title,
            "posted_date": posted_date,
            "Job Summary" : summary,
            "roles" : roles,
            "qualifications" : qualifications,
            "environment" : environment,
            "about" : about,
            "deadline" : deadline

        }
    )


with open("cedar_extracted_jobs.json", "w", encoding="utf-8") as file:
    json.dump(cleaned_jobs,file,indent=4,ensure_ascii=False)



