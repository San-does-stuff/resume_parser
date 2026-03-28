# users/urls.py  (include this in resume_parser/urls.py)

from django.urls import path
from users import views

urlpatterns = [
    # Pages
    path('auth/',            views.auth_page,       name='auth_page'),
    path('dashboard/',       views.user_dashboard,  name='user_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('logout/',          views.logout_view,     name='logout'),

    # Auth API
    path('api/auth/login/',    views.api_login,    name='api_login'),
    path('api/auth/register/', views.api_register, name='api_register'),

    # User API
    path('api/user/matches/',  views.api_user_matches, name='api_user_matches'),

    # Admin API
    path('api/admin/users/',   views.api_admin_users,  name='api_admin_users'),
]