import requests
import json
import re

url = "https://fa-ewmy-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.workLocation,requisitionList.otherWorkLocations,requisitionList.secondaryLocations,flexFieldsFacet.values,requisitionList.requisitionFlexFields&finder=findReqs;siteNumber=CX_1,facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3BTITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,limit=25,locationId=300000000464166,sortBy=POSTING_DATES_DESC"


response = requests.get(url)


if response.status_code != 200:
    print(f"Request failed with status code: {response.status_code}")
    exit()


try:
    data = response.json()
except json.JSONDecodeError:
    print("Failed to decode JSON")
    exit()

# Safely extract job list
jobs = data.get("items", [{}])[0].get("requisitionList", [])

if not jobs:
    print("No jobs found.")
    exit()

# Cleaned structured output
cleaned_jobs = []

for job in jobs:
    job_id = job.get("Id")
    title = job.get("Title")
    location = job.get("PrimaryLocation")
    country = job.get("PrimaryLocationCountry")
    workplace_type = job.get("WorkplaceType")
    posted_date = job.get("PostedDate")
    description = job.get("ShortDescriptionStr")

    url2 = f'https://fa-ewmy-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder=ById;Id={job_id},siteNumber=CX_1'
    response2 = requests.get(url2)
    try:
        data2 = response2.json()
    except json.JSONDecodeError:
        print("Failed to decode JSON")
        exit()
    category = data2.get("items",[{}])[0].get("Category")
    requisitionType = data2.get("items",[{}])[0].get("RequisitionType")
    job_ext_desc = data2.get("items",[{}])[0].get("ExternalDescriptionStr")
    job_ext_qualif = data2.get("items",[{}])[0].get("ExternalQualificationsStr")
    job_ext_resp = data2.get("items",[{}])[0].get("ExternalResponsibilitiesStr")
    

    cleaned_job_ext_desc = re.sub(r"<.*?>|&nbsp|•", "", job_ext_desc)
    cleaned_job_ext_qualif = re.sub(r"<.*?>|&nbsp|•", "", job_ext_qualif)
    cleaned_job_ext_resp = re.sub(r"<.*?>|&nbsp|•", "", job_ext_resp)

    cleaned_jobs.append({
        "company": "Verisk Nepal",
        "job_id": job_id,
        "title": title,
        "category": category,
        "requition type": requisitionType,
        "location": location,
        "country": country,
        "workplace_type": workplace_type,
        "posted_date": posted_date,
        "description": description,
        "job description": cleaned_job_ext_desc,
        "job qualification": cleaned_job_ext_qualif,
        "job responsibilities": cleaned_job_ext_resp
    })


with open("verisk_extracted_jobs.json", "w", encoding="utf-8") as file:
    json.dump(cleaned_jobs,file,indent=4,ensure_ascii=False)
