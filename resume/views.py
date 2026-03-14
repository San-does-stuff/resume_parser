from django.http import JsonResponse
from .models import Resume

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

        # store resume id in session for guest users
        request.session['resume_id'] = resume.id

        return JsonResponse({
            'message': 'File uploaded successfully',
            'resume_id': resume.id,
            'url': resume.filePath.url
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)