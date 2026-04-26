from django.db import models
from django.conf import settings

class Resume(models.Model):
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='resumes',null=True,blank=True)
    rawText    = models.TextField(blank=True)
    filePath   = models.FileField(upload_to='resume_pdfs/')
    fileType   = models.CharField(max_length=10, default='pdf')
    predicted_category = models.CharField(max_length=100, blank=True, default="")
    confidence_score = models.FloatField(default=0.0)
    uploadDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner = self.user.email if self.user else "Guest"
        return f"{owner} — {self.uploadDate}"

class Experience(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE
    )
    jobTitle = models.CharField(max_length = 255,null=True,blank=True)
    companyName = models.CharField(max_length = 255,null=True,blank=True)
    startDate = models.DateField(null=True,blank=True)
    endDate = models.DateField(null=True,blank=True)
    description = models.TextField(null=True,blank=True)

    def __str__(self):
        return f"{self.jobTitle} at {self.companyName}"
    
class Education(models.Model):
    resume = models.ForeignKey(
        Resume,
        on_delete=models.CASCADE
    )
    institution = models.CharField(max_length=255,null=True,blank=True)
    degree = models.CharField(max_length=150,blank=True,null=True)
    fieldOfStudy = models.CharField(max_length=150,blank=True,null=True)
    graduationYear = models.IntegerField(null=True,blank=True)

    def __str__(self):
        return f"{self.degree} at {self.institution}"