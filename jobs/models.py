from django.db import models
from users.models import Users

class JobCategory(models.Model):
    categoryName = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.categoryName}"
    
class Company(models.Model):
    companyName = models.CharField(max_length = 255,null=True,blank=True)
    location = models.CharField(max_length=100, blank=True, default="")
    about = models.TextField(blank=True, default="")


class Job(models.Model):
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.CASCADE
    )
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE
    )
    jobTitle = models.CharField(max_length = 255)
    job_type = models.CharField(max_length=15)
    requiredSkill = models.TextField(null=True,blank=True)
    postedDate = models.DateField(auto_now_add=True)
    deadline = models.DateField(blank=True,null=True)
    source = models.CharField(max_length=50, blank=True, default="")
    source_job_id = models.CharField(max_length=255, blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    description = models.TextField(blank=True, default="")
    content_hash = models.CharField(max_length=64, blank=True, default="")
    last_synced_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        company_name = self.company_id.companyName if self.company_id else "Unknown Company"
        return f"{self.jobTitle} at {company_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_job_id"],
                name="unique_job_per_source_identifier",
            )
        ]
    
class Recommendation(models.Model):
    users = models.ForeignKey(
        Users,
        on_delete= models.SET_NULL,
        null=True
    )
    job = models.ForeignKey(
        Job,
        on_delete=models.SET_NULL,
        null=True
    )
    recommendDate = models.DateField(auto_now_add=True)

    STATUS_CHOICES = [
    ('P', 'Pending'),
    ('A', 'Accepted'),
    ('R', 'Rejected'),
    ]
    
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='P')

    def __str__(self):
        return f"{self.users} for {self.job}"