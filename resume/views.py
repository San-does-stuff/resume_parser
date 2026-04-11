# resume/views.py

import os
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import Resume, Education, Experience
from .parser import parse_resume


@csrf_exempt
def upload_resume(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)

    file = request.FILES.get('resume')
    if not file:
        return JsonResponse({'error': 'No file uploaded'}, status=400)

    ext = file.name.split('.')[-1].lower()
    if ext not in ['pdf', 'txt']:
        return JsonResponse({'success': False,
                             'message': 'Only PDF and TXT files are supported.'})

    # Save uploaded file to database
    resume = Resume.objects.create(
        filePath = file,
        fileType = ext,
    )

    # Get full file path on disk
    file_path = os.path.join(settings.MEDIA_ROOT, resume.filePath.name)

    # Run the parser
    result = parse_resume(file_path)

    if not result['success']:
        return JsonResponse({'success': False, 'message': result['message']})

    # Save parsed fields back to resume record
    resume.rawText   = result['raw_text']
    resume.full_name = result['name']
    resume.email     = result['email']
    resume.phone     = result['phone']
    resume.skills    = ', '.join(result['skills'])
    resume.save()

    # Save education records
    for edu in result['education']:
        Education.objects.create(
            resume         = resume,
            degree         = edu.get('degree', ''),
            institution    = edu.get('institution', ''),
            graduationYear = edu.get('graduation_year'),
        )

    # Save experience records
    for exp in result['experience']:
        Experience.objects.create(
            resume      = resume,
            jobTitle    = exp.get('job_title', ''),
            companyName = exp.get('company', ''),
            startDate   = exp.get('start_date', ''),
            endDate     = exp.get('end_date', ''),
            description = exp.get('description', ''),
        )

    # Store resume id in session
    request.session['resume_id'] = resume.id

    # Return all parsed data to frontend
    return JsonResponse({
        'success':         True,
        'resume_id':       resume.id,
        'name':            result['name'],
        'email':           result['email'],
        'phone':           result['phone'],
        'skills':          result['skills'],
        'education':       result['education'],
        'experience':      result['experience'],
        'predicted_title': result['predicted_title'],
        'confidence':      result['confidence'],
    })