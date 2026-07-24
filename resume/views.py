import json

from django.http import JsonResponse
from .models import Resume
from .models import Education, Experience
from .ml.predictor import JobPredictor
from .services.pdf_parser import extract_text_from_pdf, parse_resume_text, looks_like_resume


def upload_resume(request):
    if request.method == 'POST':
        file = request.FILES.get('resume')

        if not file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        # Extract text BEFORE the file is saved through Django's storage.
        # Saving the file first can leave the file object's read position
        # in a bad state, so a second read afterwards can come back empty
        # or incomplete depending on file size and storage backend.
        raw_text = extract_text_from_pdf(file)

        # Reset the file pointer so Django can still read the file fresh
        # when it gets saved to storage below.
        file.seek(0)

        resume = Resume.objects.create(
            user=request.user if request.user.is_authenticated else None,
            filePath=file,
            fileType=file.name.split('.')[-1],
        )

        parsed_data = parse_resume_text(raw_text)
        resume.rawText = raw_text
        resume.save(update_fields=["rawText"])

        # Reset and repopulate parsed relation rows for this upload.
        Experience.objects.filter(resume=resume).delete()
        Education.objects.filter(resume=resume).delete()

        for exp in parsed_data.get("experience", []):
            Experience.objects.create(
                resume=resume,
                jobTitle=exp.get("job_title"),
                companyName=exp.get("company_name"),
                description=exp.get("description"),
            )

        for edu in parsed_data.get("education", []):
            Education.objects.create(
                resume=resume,
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                fieldOfStudy=edu.get("field_of_study"),
                graduationYear=edu.get("graduation_year"),
            )

        # Before running the job-category model, check whether this file
        # actually looks like a resume at all. If it doesn't (a random
        # PDF has no email/phone/skills/education/experience we could
        # find), skip prediction instead of forcing a guess.
        if not looks_like_resume(parsed_data, raw_text):
            top_predictions = [{"job_category": "Not a Resume", "confidence": 0.0}]
            model_accuracy = 0.0
        else:
            skills_text = " ".join(parsed_data.get("skills", []))
            education_text = " ".join((item.get("degree") or "") for item in parsed_data.get("education", []))
            experience_text = " ".join((item.get("job_title") or "") for item in parsed_data.get("experience", []))
            predictor = JobPredictor()
            top_predictions = predictor.predict_top_jobs(
                resume_text=raw_text,
                skills=skills_text,
                education=education_text,
                experience=experience_text,
                top_n=3,
            )
            model_accuracy = predictor.model_accuracy

        # The single "best guess" is just the first item in the top list.
        # We still store this one on the Resume model, since the model
        # only needs one predicted_category value.
        best_prediction = top_predictions[0]
        resume.predicted_category = best_prediction["job_category"]
        resume.confidence_score = best_prediction["confidence"]
        resume.save(update_fields=["predicted_category", "confidence_score"])

        prediction = {
            "job_category": best_prediction["job_category"],
            "confidence": best_prediction["confidence"],
            "model_accuracy": model_accuracy,
        }

        # store resume id in session for guest users
        request.session['resume_id'] = resume.id
        request.session['latest_extracted_data'] = parsed_data
        request.session['latest_prediction'] = prediction
        request.session['latest_top_predictions'] = top_predictions
        request.session['latest_resume_url'] = resume.filePath.url

        return JsonResponse({
            'message': 'File uploaded successfully',
            'resume_id': resume.id,
            'url': resume.filePath.url,
            'extracted_data': parsed_data,
            'prediction': prediction,
            'top_predictions': top_predictions,
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


def update_prediction(request):
    """
    Re-run the job-category model using only a specific set of skills the
    user has chosen to highlight, instead of everything originally
    extracted from the resume. This lets someone narrow down the
    prediction by focusing on a subset of their skills.

    Expects a POST with a JSON body like:
        {"resume_id": 12, "selected_skills": ["python", "django", "sql"]}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    resume_id = body.get('resume_id') or request.session.get('resume_id')
    selected_skills = body.get('selected_skills', [])

    if not resume_id:
        return JsonResponse({'error': 'No resume_id provided'}, status=400)

    try:
        resume = Resume.objects.get(id=resume_id)
    except Resume.DoesNotExist:
        return JsonResponse({'error': 'Resume not found'}, status=404)

    if not isinstance(selected_skills, list) or len(selected_skills) == 0:
        return JsonResponse({'error': 'No skills selected'}, status=400)

    skills_text = " ".join(str(skill) for skill in selected_skills)

    # Education and experience stay the same as what was already parsed
    # from the resume -- only the skill set changes here.
    education_entries = Education.objects.filter(resume=resume)
    education_text = " ".join((entry.degree or "") for entry in education_entries)

    experience_entries = Experience.objects.filter(resume=resume)
    experience_text = " ".join((entry.jobTitle or "") for entry in experience_entries)

    predictor = JobPredictor()
    top_predictions = predictor.predict_top_jobs(
        # We deliberately leave resume_text empty here. If we passed the
        # full original resume text, every skill that was ever mentioned
        # (including the ones the user just deselected) would still be
        # feeding into the model through the free-form text, defeating
        # the point of narrowing down by skill.
        resume_text="",
        skills=skills_text,
        education=education_text,
        experience=experience_text,
        top_n=3,
    )

    best_prediction = top_predictions[0]
    resume.predicted_category = best_prediction["job_category"]
    resume.confidence_score = best_prediction["confidence"]
    resume.save(update_fields=["predicted_category", "confidence_score"])

    prediction = {
        "job_category": best_prediction["job_category"],
        "confidence": best_prediction["confidence"],
        "model_accuracy": predictor.model_accuracy,
    }

    request.session['latest_prediction'] = prediction
    request.session['latest_top_predictions'] = top_predictions

    return JsonResponse({
        'message': 'Prediction updated',
        'resume_id': resume.id,
        'prediction': prediction,
        'top_predictions': top_predictions,
    })