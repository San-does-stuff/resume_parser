from django.contrib import admin
from .models import Education, Experience, Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "fileType", "predicted_category", "confidence_score", "uploadDate")
    search_fields = ("user__email", "user__username")


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ("id", "resume", "jobTitle", "companyName")
    search_fields = ("jobTitle", "companyName")


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ("id", "resume", "degree", "institution", "graduationYear")
    search_fields = ("degree", "institution", "fieldOfStudy")
