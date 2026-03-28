# users/views.py

import json
import hashlib
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UserProfile, JobVacancy, JobMatch


# ── helper: hash passwords ───────────────────────────────
def hash_password(plain):
    return hashlib.sha256(plain.encode()).hexdigest()

def check_password(plain, hashed):
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


# ── AUTH PAGES ───────────────────────────────────────────

def auth_page(request):
    if request.session.get('user_id'):
        if request.session.get('is_admin'):
            return redirect('admin_dashboard')
        return redirect('user_dashboard')
    return render(request, 'auth.html')


def logout_view(request):
    request.session.flush()
    return redirect('auth_page')


# ── AUTH API ─────────────────────────────────────────────

@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data     = json.loads(request.body)
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    # Admin login — change these credentials as needed
    if email == 'admin@gmail.com' and password == 'admin123':
        request.session['is_admin']  = True
        request.session['user_id']   = 0
        request.session['user_name'] = 'Admin'
        return JsonResponse({'success': True, 'redirect': '/admin-dashboard/'})

    try:
        user = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Incorrect email or password.'}, status=401)

    if not check_password(password, user.password):
        return JsonResponse({'success': False, 'message': 'Incorrect email or password.'}, status=401)

    request.session['user_id']   = user.id
    request.session['user_name'] = user.full_name
    request.session['is_admin']  = False
    return JsonResponse({'success': True, 'redirect': '/dashboard/'})


@csrf_exempt
def api_register(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data      = json.loads(request.body)
    full_name = data.get('full_name', '').strip()
    email     = data.get('email', '').strip().lower()
    password  = data.get('password', '')

    if not full_name or not email or not password:
        return JsonResponse({'success': False, 'message': 'All fields are required.'}, status=400)

    if UserProfile.objects.filter(email=email).exists():
        return JsonResponse({'success': False, 'message': 'Email already registered.'}, status=409)

    UserProfile.objects.create(
        full_name=full_name,
        email=email,
        password=hash_password(password)
    )
    return JsonResponse({'success': True}, status=201)


# ── DASHBOARD PAGES ──────────────────────────────────────

def admin_dashboard(request):
    if not request.session.get('is_admin'):
        return redirect('auth_page')
    return render(request, 'admin_dashboard.html')


def user_dashboard(request):
    if not request.session.get('user_id'):
        return redirect('auth_page')
    if request.session.get('is_admin'):
        return redirect('admin_dashboard')
    return render(request, 'user_dashboard.html')


# ── ADMIN API ────────────────────────────────────────────

def api_admin_users(request):
    if not request.session.get('is_admin'):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    users = UserProfile.objects.all().order_by('-created_at')
    data  = [{
        'id':          u.id,
        'full_name':   u.full_name,
        'email':       u.email,
        'joined':      u.created_at.strftime('%Y-%m-%d'),
        'match_count': u.matches.count(),
    } for u in users]

    return JsonResponse({'users': data})


# ── USER API ─────────────────────────────────────────────

def api_user_matches(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)

    matches = JobMatch.objects.filter(user_id=user_id).select_related('vacancy')
    data    = [{
        'job_title': m.vacancy.title,
        'company':   m.vacancy.company,
        'location':  m.vacancy.location,
        'score':     m.match_score,
        'skills':    m.vacancy.required_skills,
    } for m in matches]

    return JsonResponse({'matches': data})