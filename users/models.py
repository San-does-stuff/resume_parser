# users/models.py

from django.db import models

class UserProfile(models.Model):

    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user',  'User'),
    ]

    full_name  = models.CharField(max_length=150)
    email      = models.EmailField(unique=True)
    password   = models.CharField(max_length=255)
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_admin(self):
        return self.role == 'admin'

    def __str__(self):
        return f"{self.full_name} ({self.role})"

Users = UserProfile


class JobVacancy(models.Model):
    """
    Stores job vacancies scraped/added from companies.
    """
    title          = models.CharField(max_length=200)
    company        = models.CharField(max_length=200)
    location       = models.CharField(max_length=200, blank=True)
    description    = models.TextField(blank=True)
    required_skills = models.JSONField(default=list)   # e.g. ["Python", "Django"]
    is_active      = models.BooleanField(default=True)
    posted_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} at {self.company}"


class JobMatch(models.Model):
    user         = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='matches')
    vacancy      = models.ForeignKey(JobVacancy,  on_delete=models.CASCADE, related_name='matches')
    match_score  = models.FloatField(default=0.0)
    matched_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_score']

    def __str__(self):
        return f"{self.user.full_name} → {self.vacancy.title} ({int(self.match_score * 100)}%)"


#Users = UserProfile   # ← no indentation, outside all classes