from django.http import JsonResponse
from .models import Resume
from .models import Education, Experience
from .ml.predictor import JobPredictor
from .services.pdf_parser import extract_text_from_pdf, parse_resume_text

def upload_resume(request):
    if request.method == 'POST':
        file = request.FILES.get('resume')

        if not file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        resume = Resume.objects.create(
            user=request.user if request.user.is_authenticated else None,
            filePath=file,
            fileType=file.name.split('.')[-1],
        )

        raw_text = extract_text_from_pdf(file)
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

        skills_text = " ".join(parsed_data.get("skills", []))
        education_text = " ".join((item.get("degree") or "") for item in parsed_data.get("education", []))
        experience_text = " ".join((item.get("job_title") or "") for item in parsed_data.get("experience", []))
        predictor = JobPredictor()
        prediction = predictor.predict_job(
            resume_text=raw_text,
            skills=skills_text,
            education=education_text,
            experience=experience_text,
        )
        resume.predicted_category = prediction["job_category"]
        resume.confidence_score = prediction["confidence"]
        resume.save(update_fields=["predicted_category", "confidence_score"])

        # store resume id in session for guest users
        request.session['resume_id'] = resume.id
        request.session['latest_extracted_data'] = parsed_data
        request.session['latest_prediction'] = prediction
        request.session['latest_resume_url'] = resume.filePath.url

        return JsonResponse({
            'message': 'File uploaded successfully',
            'resume_id': resume.id,
            'url': resume.filePath.url,
            'extracted_data': parsed_data,
            'prediction': prediction,
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)