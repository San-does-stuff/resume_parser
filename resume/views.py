from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage
# from django.views.decorators.csrf import csrf_exempt

# @csrf_exempt
def upload_resume(request):
    if request.method == 'POST':    
        file = request.FILES.get('resume')

        if not file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        fs = FileSystemStorage()          
        filename = fs.save(file.name, file)
        file_url = fs.url(filename)

        return JsonResponse({
            'message': 'File uploaded successfully',
            'filename': filename,
            'url': file_url
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)