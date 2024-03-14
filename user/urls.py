from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views
urlpatterns = [
    path('register-admin/', views.register_admin),
    path('create-user/', views.create_user),
    path('verify-user-otp/', views.verify_user_otp),
    path('resend-verification-otp/', views.resend_otp),
    path('auth/token',views.get_token),
    path('auth/token/refresh',TokenRefreshView.as_view(),),
    path("user-profile/",views.user_profile),
    path("user-list",views.users),
    path("roles/",views.user_roles),
    path("grant-permission/", views.grant_permission_to_user),
    path("create-permission-set/", views.create_permission_set),
    path("excel-to-dict", views.excel_to_dict),
]