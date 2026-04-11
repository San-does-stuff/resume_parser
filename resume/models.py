from django.db import models

class Resume(models.Model):
    full_name  = models.CharField(max_length=150, blank=True)
    email      = models.CharField(max_length=150, blank=True)
    phone      = models.CharField(max_length=30,  blank=True)
    skills     = models.TextField(blank=True)   # stored as comma-separated
    rawText    = models.TextField(blank=True)
    filePath   = models.FileField(upload_to='resume_pdfs/')
    fileType   = models.CharField(max_length=10, default='pdf')
    uploadDate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} — {self.uploadDate}"


class Experience(models.Model):
    resume      = models.ForeignKey(Resume, on_delete=models.CASCADE)
    jobTitle    = models.CharField(max_length=255, null=True, blank=True)
    companyName = models.CharField(max_length=255, null=True, blank=True)
    startDate   = models.CharField(max_length=20,  null=True, blank=True)
    endDate     = models.CharField(max_length=20,  null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.jobTitle} at {self.companyName}"


class Education(models.Model):
    resume         = models.ForeignKey(Resume, on_delete=models.CASCADE)
    institution    = models.CharField(max_length=255, null=True, blank=True)
    degree         = models.CharField(max_length=150, null=True, blank=True)
    graduationYear = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.degree} at {self.institution}"