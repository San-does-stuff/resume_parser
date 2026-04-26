from django.contrib import admin
from .models import Company, Job, JobCategory, Recommendation


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "categoryName")
    search_fields = ("categoryName",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "companyName", "location")
    search_fields = ("companyName", "location")


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "jobTitle", "category", "company_id", "job_type", "postedDate", "deadline")
    search_fields = ("jobTitle", "requiredSkill")
    list_filter = ("category", "job_type")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("id", "users", "job", "status", "recommendDate")
    list_filter = ("status", "recommendDate")
