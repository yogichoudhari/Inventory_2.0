from django.urls import path
from . import views
urlpatterns = [
    path('register/', views.register_admin),
    path('create-user/', views.create_user),
    path('verify/', views.verify),
    path('resend-otp/', views.resend_otp),
    path('login/',views.login,),
    path("user-profile/",views.user_profile),
    path("user-list",views.users),
    path("grant-permission/", views.grant_permission_to_user),
    path("create-permission-set/", views.create_permission_set),
]