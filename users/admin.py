from django.contrib import admin
from .models import Users


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "fullname", "phone", "location", "is_active", "is_staff")
    search_fields = ("username", "email", "fullname", "phone")
