from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from resume.models import Resume

from .models import Job, Recommendation
from .services import (
    build_match_reasons,
    get_recommended_jobs_for_prediction,
    run_scrapers_and_sync_jobs,
)


@login_required
def recommended_jobs(request):
    run_scrapers_and_sync_jobs()
    latest_resume = (
        Resume.objects.filter(user=request.user)
        .order_by("-uploadDate")
        .first()
    )

    if not latest_resume or not latest_resume.predicted_category:
        all_recs = Recommendation.objects.filter(users=request.user)
        return render(
            request,
            "jobs/recommendations.html",
            {
                "jobs": [],
                "all_jobs": Job.objects.select_related("company_id", "category").all(),
                "predicted_category": "",
                "confidence_score": 0.0,
                "message": "Upload a resume first to get recommendations.",
                "resume_count": Resume.objects.filter(user=request.user).count(),
                "recommendation_count": all_recs.count(),
                "accepted_count": all_recs.filter(status="A").count(),
                "pending_count": all_recs.filter(status="P").count(),
                "latest_resume_date": None,
            },
        )

    jobs = get_recommended_jobs_for_prediction(
        latest_resume.predicted_category
    )
    all_jobs = Job.objects.select_related("company_id", "category").all()
    for job in jobs:
        job.match_reasons = build_match_reasons(job, latest_resume.predicted_category)

    for job in jobs:
        Recommendation.objects.get_or_create(
            users=request.user,
            job=job,
            defaults={"status": "P"},
        )

    all_recs = Recommendation.objects.filter(users=request.user)

    return render(
        request,
        "jobs/recommendations.html",
        {
            "jobs": jobs,
            "all_jobs": all_jobs,
            "predicted_category": latest_resume.predicted_category,
            "confidence_score": latest_resume.confidence_score,
            "message": "",
            "resume_count": Resume.objects.filter(user=request.user).count(),
            "recommendation_count": all_recs.count(),
            "accepted_count": all_recs.filter(status="A").count(),
            "pending_count": all_recs.filter(status="P").count(),
            "latest_resume_date": latest_resume.uploadDate,
        },
    )
