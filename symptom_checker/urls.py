from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include
from django.conf.urls.static import static
from django.views.i18n import set_language
from django.views.generic import TemplateView


app_name = 'symptom_checker'

urlpatterns = [
   path('set_language/', set_language, name='set_language'),   

    path('start/', views.start_symptom_check, name='start_symptom_check'),
    path('start/step/<int:step>/', views.start_symptom_check, name='start_symptom_check_step'),
 
    path("symptom/<int:session_id>/", views.symptom_chat, name="symptom_chat"), 
   
    path("my_symptom_checks/", views.my_symptom_checks, name="my_symptom_checks"), 
    path('summary/<int:session_id>/', views.symptom_summary_view, name='symptom_summary'), 
    path('download-summary/<int:session_id>/', views.download_symptom_summary_pdf, name='download_symptom_pdf'),
    path("delete_empty_sessions/", views.delete_empty_sessions, name="delete_empty_sessions"), 

     path('disclaimer/', views.DisclaimerView.as_view(), name='disclaimer'),
    path('terms/', TemplateView.as_view(template_name="legal/terms.html"), name='terms'),
    path('privacy/', TemplateView.as_view(template_name="legal/privacy.html"), name='privacy'),
  
]

