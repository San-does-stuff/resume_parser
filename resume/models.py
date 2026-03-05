from django.db import models
from django.conf import settings

class Resume(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resumes')
    rawText    = models.TextField(blank=True)
    filePath   = models.FileField(upload_to='resume_pdfs/')
    fileType   = models.CharField(max_length=10, default='pdf')
    uploadDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.uploadDate}"
