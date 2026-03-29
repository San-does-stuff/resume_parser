# users/views.py

import json
import hashlib
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import UserProfile


# ── helpers ──────────────────────────────────────────────
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
    return render(request, 'admin_dashboard.html', {
        'admin_name': request.session.get('user_name', 'Admin')
    })


def user_dashboard(request):
    if not request.session.get('user_id'):
        return redirect('auth_page')
    if request.session.get('is_admin'):
        return redirect('admin_dashboard')

    user_id = request.session.get('user_id')
    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        request.session.flush()
        return redirect('auth_page')

    return render(request, 'user_dashboard.html', {'user': user})


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


@csrf_exempt
def api_admin_edit_user(request):
    if not request.session.get('is_admin'):
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
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)

    if UserProfile.objects.filter(email=email).exclude(id=user_id).exists():
        return JsonResponse({'success': False, 'message': 'Email already in use by another user.'})

    user.full_name = name
    user.email     = email
    if password:
        user.password = hash_password(password)
    user.save()

    return JsonResponse({'success': True})


@csrf_exempt
def api_admin_delete_user(request):
    if not request.session.get('is_admin'):
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    data    = json.loads(request.body)
    user_id = data.get('id')

    try:
        user = UserProfile.objects.get(id=user_id)
        user.delete()
        return JsonResponse({'success': True})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=404)


# ── USER API ─────────────────────────────────────────────

def api_user_matches(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Not logged in'}, status=401)

    from jobs.models import Recommendation

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return JsonResponse({'matches': []})

    recs = Recommendation.objects.filter(
        users=user
    ).select_related('job', 'job__category')

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
    """Return whether the logged-in user has already uploaded a CV."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'cv_uploaded': False})

    try:
        user = UserProfile.objects.get(id=user_id)
    except UserProfile.DoesNotExist:
        return JsonResponse({'cv_uploaded': False})

    # Check if a CV file exists for this user
    cv_path = os.path.join(settings.MEDIA_ROOT, 'cvs', f'user_{user_id}')
    cv_uploaded = os.path.exists(cv_path) and bool(os.listdir(cv_path))

    return JsonResponse({
        'cv_uploaded': cv_uploaded,
        'filename': user.cv_filename if hasattr(user, 'cv_filename') else ''
    })


@csrf_exempt
def api_upload_cv(request):
    """Receive CV file, save it, and run NLP parser."""
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in.'}, status=401)

    cv_file = request.FILES.get('cv')
    if not cv_file:
        return JsonResponse({'success': False, 'message': 'No file received.'}, status=400)

    # Validate file type
    allowed = ['.pdf', '.doc', '.docx']
    ext     = os.path.splitext(cv_file.name)[1].lower()
    if ext not in allowed:
        return JsonResponse({'success': False, 'message': 'Only PDF, DOC and DOCX files are allowed.'})

    # Save file to media/cvs/user_<id>/
    save_dir = os.path.join(settings.MEDIA_ROOT, 'cvs', f'user_{user_id}')
    os.makedirs(save_dir, exist_ok=True)

    # Remove old CV if exists
    for old_file in os.listdir(save_dir):
        os.remove(os.path.join(save_dir, old_file))

    save_path = os.path.join(save_dir, cv_file.name)
    with open(save_path, 'wb') as f:
        for chunk in cv_file.chunks():
            f.write(chunk)

    # ── Run your NLP parser here ──────────────────────────
    # from resume.parser import extract_skills
    # skills = extract_skills(save_path)
    # Store skills back on the user or a related model
    # ─────────────────────────────────────────────────────

    return JsonResponse({
        'success':  True,
        'filename': cv_file.name,
        'message':  'CV uploaded and parsed successfully.'
    })