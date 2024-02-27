from django.urls import path
from . import views
urlpatterns = [
    path('register-admin/', views.register_admin),
    path('create-user/', views.create_user),
    path('verify-user-otp/', views.verify_user_otp),
    path('resend-verification-otp/', views.resend_otp),
    path('login/',views.login,),
    path("user-profile/",views.user_profile),
    path("user-list",views.users),
    path("roles/",views.user_roles),
    path("grant-permission/", views.grant_permission_to_user),
    path("create-permission-set/", views.create_permission_set),
]