# users/views.py

import json
import hashlib
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import UserProfile


def hash_password(plain):
    return hashlib.sha256(plain.encode()).hexdigest()

def check_password(plain, hashed):
    return hashlib.sha256(plain.encode()).hexdigest() == hashed


# ── AUTH ─────────────────────────────────────────────────

def auth_page(request):
    if request.session.get('user_id'):
        if request.session.get('role') == 'admin':
            return redirect('admin_dashboard')
        return redirect('user_dashboard')
    return render(request, 'auth.html')


def logout_view(request):
    request.session.flush()
    return redirect('auth_page')


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data     = json.loads(request.body)
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    try:
        user = UserProfile.objects.get(email=email)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Incorrect email or password.'}, status=401)

    if not check_password(password, user.password):
        return JsonResponse({'success': False, 'message': 'Incorrect email or password.'}, status=401)

    # Store role in session
    request.session['user_id']   = user.id
    request.session['user_name'] = user.full_name
    request.session['role']      = user.role

    redirect_url = '/admin-dashboard/' if user.role == 'admin' else '/dashboard/'
    return JsonResponse({'success': True, 'redirect': redirect_url})


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

    # Always register as user — never admin
    UserProfile.objects.create(
        full_name = full_name,
        email     = email,
        password  = hash_password(password),
        role      = 'user'
    )
    return JsonResponse({'success': True}, status=201)


# ── ROLE GUARD helpers ────────────────────────────────────

def is_admin_session(request):
    return request.session.get('role') == 'admin'

def is_user_session(request):
    return request.session.get('role') == 'user' and request.session.get('user_id')


# ── DASHBOARD PAGES ───────────────────────────────────────

def admin_dashboard(request):
    if not is_admin_session(request):
        return redirect('auth_page')
    return render(request, 'admin_dashboard.html')


def user_dashboard(request):
    if not is_user_session(request):
        return redirect('auth_page')

    try:
        user = UserProfile.objects.get(id=request.session['user_id'])
    except UserProfile.DoesNotExist:
        request.session.flush()
        return redirect('auth_page')

    return render(request, 'user_dashboard.html', {'user': user})


# ── ADMIN API — only admins can call these ────────────────

def api_admin_users(request):
    if not is_admin_session(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    # Exclude admins — only show regular users
    users = UserProfile.objects.filter(role='user').order_by('-created_at')
    data  = [{
        'id':          u.id,
        'full_name':   u.full_name,
        'email':       u.email,
        'role':        u.role,
        'joined':      u.created_at.strftime('%Y-%m-%d'),
        'match_count': u.matches.count(),
    } for u in users]

    return JsonResponse({'users': data})


@csrf_exempt
def api_admin_edit_user(request):
    if not is_admin_session(request):
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data     = json.loads(request.body)
    user_id  = data.get('id')
    name     = data.get('full_name', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()

    if not name or not email:
        return JsonResponse({'success': False, 'message': 'Name and email are required.'})

    try:
        user = UserProfile.objects.get(id=user_id, role='user')  # can only edit users
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)

    if UserProfile.objects.filter(email=email).exclude(id=user_id).exists():
        return JsonResponse({'success': False, 'message': 'Email already in use.'})

    user.full_name = name
    user.email     = email
    if password:
        user.password = hash_password(password)
    user.save()

    return JsonResponse({'success': True})


@csrf_exempt
def api_admin_delete_user(request):
    if not is_admin_session(request):
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data    = json.loads(request.body)
    user_id = data.get('id')

    try:
        user = UserProfile.objects.get(id=user_id, role='user')  # can only delete users
        user.delete()
        return JsonResponse({'success': True})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)


# ── USER API — only users can call these ──────────────────

def api_user_matches(request):
    if not is_user_session(request):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    from jobs.models import Recommendation
    try:
        user = UserProfile.objects.get(id=request.session['user_id'])
    except UserProfile.DoesNotExist:
        return JsonResponse({'matches': []})

    recs = Recommendation.objects.filter(users=user).select_related('job', 'job__category')
    data = []
    for r in recs:
        job    = r.job
        skills = [s.strip() for s in job.requiredSkill.split(',')] if job.requiredSkill else []
        data.append({
            'job_title':   job.jobTitle    or '',
            'company':     job.companyName or '',
            'category':    job.category.categoryName if job.category else '',
            'skills':      skills,
            'posted_date': job.postedDate.strftime('%Y-%m-%d') if job.postedDate else '',
            'status':      r.get_status_display(),
        })

    return JsonResponse({'matches': data})


def api_cv_status(request):
    if not is_user_session(request):
        return JsonResponse({'cv_uploaded': False})

    user_id  = request.session['user_id']
    cv_path  = os.path.join(settings.MEDIA_ROOT, 'cvs', f'user_{user_id}')
    uploaded = os.path.exists(cv_path) and bool(os.listdir(cv_path))
    return JsonResponse({'cv_uploaded': uploaded})


@csrf_exempt
def api_upload_cv(request):
    if not is_user_session(request):
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    cv_file = request.FILES.get('cv')
    if not cv_file:
        return JsonResponse({'success': False, 'message': 'No file received.'}, status=400)

    ext = os.path.splitext(cv_file.name)[1].lower()
    if ext not in ['.pdf', '.doc', '.docx']:
        return JsonResponse({'success': False, 'message': 'Only PDF, DOC and DOCX allowed.'})

    user_id  = request.session['user_id']
    save_dir = os.path.join(settings.MEDIA_ROOT, 'cvs', f'user_{user_id}')
    os.makedirs(save_dir, exist_ok=True)

    for old in os.listdir(save_dir):
        os.remove(os.path.join(save_dir, old))

    with open(os.path.join(save_dir, cv_file.name), 'wb') as f:
        for chunk in cv_file.chunks():
            f.write(chunk)

    return JsonResponse({'success': True, 'filename': cv_file.name})