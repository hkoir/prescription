from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CustomTokenObtainPairView
from django.contrib.auth import views as auth_views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

app_name = 'mobile_api' 


urlpatterns = [
    path('signup/', views.signup,name='signup'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
     path('save-token/', views.save_fcm_token,name='save_token'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('auto-login-view/', views.auto_login_view, name='auto_login'),
    path('api/get-auto-login-token/', views.get_auto_login_token, name='get_auto_login_token'),

    path('api/doctor/profile/', views.doctor_profile_view, name='doctor-profile'),   
    path("api/doctors/me/", views.DoctorProfileMeView.as_view(), name="doctor-me"),
    path("api/auth/user/", views.user_info_view, name="api-auth-user"),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    ################ chat api #############################
   path("threads/", views.ChatThreadListView.as_view(), name="chat-thread-list"),
    path("threads/<int:thread_id>/messages/", views.ChatMessageListView.as_view(), name="chat-message-list"),
    path("messages/send/", views.SendMessageAPIView.as_view(), name="chat-message-send"),

]  
