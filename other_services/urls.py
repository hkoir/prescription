from django.urls import path
from . import views

app_name = 'other_services'

urlpatterns = [
     path('nearby_services/', views.nearby_service_list, name='service_list'),
     path("elf-health-check/", views.self_health_check, name="self_health_check"),
    path("api/self-health-check/", views.self_health_check_api, name="self_health_check_api"),
  
]

