from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from resume.models import Resume

from .models import Users


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        fullname = request.POST.get("fullname", "").strip()
        phone = request.POST.get("phone", "").strip()
        location = request.POST.get("location", "").strip()

        if not username or not email or not password:
            messages.error(request, "Username, email, and password are required.")
            return render(request, "users/register.html")

        if Users.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "users/register.html")

        if Users.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, "users/register.html")

        user = Users.objects.create_user(
            username=username,
            email=email,
            password=password,
            fullname=fullname,
            phone=phone,
            location=location,
        )
        login(request, user)
        _attach_session_resume_to_user(request, user)
        _clear_resume_session_state(request)
        return redirect("recommended_jobs")

    return render(request, "users/register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "users/login.html")

        login(request, user)
        _attach_session_resume_to_user(request, user)
        _clear_resume_session_state(request)
        return redirect("recommended_jobs")

    return render(request, "users/login.html")


@login_required
def logout_view(request):
    _clear_resume_session_state(request)
    logout(request)
    return redirect("home")


def _attach_session_resume_to_user(request, user):
    resume_id = request.session.get("resume_id")
    if not resume_id:
        return

    resume = Resume.objects.filter(id=resume_id).first()
    if resume and resume.user is None:
        resume.user = user
        resume.save(update_fields=["user"])


def _clear_resume_session_state(request):
    for key in ("resume_id", "latest_extracted_data", "latest_prediction", "latest_resume_url"):
        request.session.pop(key, None)
