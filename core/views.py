from django.shortcuts import render
from django.conf import settings
from pathlib import Path
from resume.models import Resume
from resume.services.pdf_parser import parse_resume_text

def home(request):
    initial_state = {
        "extracted_data": {},
        "prediction": {},
        "resume_url": "",
    }

    session_extracted = request.session.get("latest_extracted_data")
    session_prediction = request.session.get("latest_prediction")
    session_resume_url = request.session.get("latest_resume_url")

    if request.user.is_authenticated:
        latest_resume = (
            Resume.objects.filter(user=request.user)
            .prefetch_related("experience_set", "education_set")
            .order_by("-uploadDate")
            .first()
        )
        if latest_resume:
            parsed = parse_resume_text(latest_resume.rawText or "")
            db_experience = [
                {
                    "job_title": exp.jobTitle,
                    "company_name": exp.companyName,
                    "description": exp.description,
                }
                for exp in latest_resume.experience_set.all()
            ]
            db_education = [
                {
                    "degree": edu.degree,
                    "institution": edu.institution,
                    "field_of_study": edu.fieldOfStudy,
                    "graduation_year": edu.graduationYear,
                }
                for edu in latest_resume.education_set.all()
            ]

            # Keep parser output when legacy DB rows are empty.
            if db_experience:
                parsed["experience"] = db_experience
            if db_education:
                parsed["education"] = db_education
            initial_state["extracted_data"] = parsed
            initial_state["prediction"] = {
                "job_category": latest_resume.predicted_category,
                "confidence": latest_resume.confidence_score,
            }
            if latest_resume.filePath and latest_resume.filePath.storage.exists(latest_resume.filePath.name):
                initial_state["resume_url"] = latest_resume.filePath.url
    elif session_extracted or session_prediction or session_resume_url:
        # Guest users can continue from same-browser uploads.
        initial_state["extracted_data"] = session_extracted or {}
        initial_state["prediction"] = session_prediction or {}
        if _media_url_exists(session_resume_url):
            initial_state["resume_url"] = session_resume_url or ""

    context = {
        "initial_resume_state": initial_state,
        "initial_pdf_url": initial_state["resume_url"],
    }
    return render(request, "home.html", context)


def _media_url_exists(url: str | None) -> bool:
    if not url:
        return False
    media_prefix = settings.MEDIA_URL or "/media/"
    if not url.startswith(media_prefix):
        # Static/default PDFs are handled by template fallback.
        return False
    relative_path = url[len(media_prefix):]
    if not relative_path:
        return False
    return (Path(settings.MEDIA_ROOT) / relative_path).exists()
