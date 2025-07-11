from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('doctor/earnings/', views.doctor_earnings_view, name='doctor_earnings'),
    path('doctor/profile/', views.doctor_profile, name='doctor_profile'),    
      
    path('enroll_doctor/', views.create_doctor_profile, name='enroll_doctor'),
    path('create_doctor_profile/', views.manage_doctor_profile, name='create_doctor_profile'),
    path('update_mdoctor_profile/<int:id>/', views.manage_doctor_profile, name='update_doctor_profile'),
    path('delete_doctor_profile/<int:id>/', views.delete_doctor_profile, name='delete_doctor_profile'),

    path('doctor/detail/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),

    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('update_patient_profile/<int:patient_id>/', views.update_patient_profile, name='update_patient_profile'),    
    path('patient/detail/<int:patient_id>/', views.patient_detail, name='patient_detail'),

    path('doctor-payments-list/', views.doctor_payment_list, name='doctor_payment_list'),
    path('confirm-payment-status/<int:payment_id>/', views.confirm_payment_status, name='confirm_payment_status'),
    path('create-manual-doctor-payment/<int:doctor_id>/', views.create_manual_doctor_payment, name='create_manual_doctor_payment'),
    path('doctor_payment_detail/<int:doctor_id>/', views.doctor_payment_detail, name='doctor_payment_detail'),

  
]

