from django.urls import path
from . import views

app_name = 'other_services'

urlpatterns = [
     path('nearby_services/', views.nearby_service_list, name='service_list'),
  
]

