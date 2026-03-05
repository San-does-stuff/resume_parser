from django.db import models
from users.models import Users

class JobCategory(models.Model):
    categoryName = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.categoryName}"

class Job(models.Model):
    category = models.ForeignKey(
        JobCategory,
        on_delete=models.CASCADE
    )
    jobTitle = models.CharField(max_length = 255,null=True,blank=True)
    companyName = models.CharField(max_length = 255,null=True,blank=True)
    requiredSkill = models.TextField(null=True,blank=True)
    postedDate = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.jobTitle} at {self.companyName}"
    
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