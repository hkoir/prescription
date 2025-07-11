from django.urls import path
from . import views

app_name = 'prescription'

urlpatterns = [

    path('', views.home, name='home'),
    path('available_doctors/', views.available_doctors, name='available_doctors'), 
    path('create_ai_prescription/', views.create_ai_prescription, name='create_ai_prescription'),
    path('<int:pk>/', views.ai_prescription_detail, name='ai_prescription_detail'),
    path('ai_prescription_list/', views.ai_prescription_list, name='ai_prescription_list'), 
    path('ai_prescription_pdf/<int:pk>/', views.ai_prescription_pdf, name='ai_prescription_pdf'), 

    path('create_ai_prescription_with_image/', views.create_ai_prescription_with_image, name='create_ai_prescription_with_image'),
    path('lab_image_interpretation_view/', views.lab_image_interpretation_view, name='lab_image_interpretation_view'),
    path('lab-test-interpretations/history/', views.lab_interpretation_history, name='lab_interpretation_history'),


    path('prescription/<int:pk>/book_doctor/', views.book_doctor, name='book_doctor'),
    path('book_doctor_direct/<int:pk>/', views.book_doctor_direct, name='book_doctor_direct'),
    path('prescription/<int:prescription_id>/confirm_booking/<int:doctor_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking-success/<int:doctor_id>/<int:booking_id>/', views.doctor_booking_success, name='doctor_booking_success'),
    path('request_video_call/<int:booking_id>/', views.request_video_call, name='request_video_call'), 
    path('approve_request_video_call/<int:booking_id>/', views.approve_request_video_call, name='approve_request_video_call'),   
   
    path('doctor-bookings-list/', views.doctor_bookings_list, name='doctor_bookings_list'),
    path('doctor-bookings-detail/<int:pk>/', views.doctor_booking_detail, name='doctor_booking_detail'),
    path('doctor-followup_bookings-detail/<int:pk>/', views.doctor_followup_booking_detail, name='doctor_followup_booking_detail'),
   
    path('bookings/<int:booking_id>/prescription/', views.create_doctor_prescription, name='create_doctor_prescription'),
    path('prescription/create/<int:booking_id>/followup/<int:followup_id>/',views.create_doctor_prescription, name='create_followup_doctor_prescription'),

    path('doctor_prescription_list/', views.doctor_prescription_list, name='doctor_prescription_list'),
    path('prescriptions/<int:pk>/', views.doctor_prescription_detail, name='doctor_prescription_detail'),
    path('doctor_prescription_pdf/<int:pk>/', views.doctor_prescription_pdf, name='doctor_prescription_pdf'), 
    path('prescription_single/<int:pk>/', views.doctor_prescription_detail_single, name='doctor_prescription_detail_single'),
    path('followup/<int:followup_id>/', views.followup_prescription_detail_single, name='followup_prescription_detail_single'), 
    path('doctor_followup_prescription_pdf/<int:pk>/', views.doctor_followup_prescription_pdf, name='doctor_followup_prescription_pdf'), 

    path('video-call/<int:booking_id>/', views.video_consultation_prescription, name='video_call'),

    path('request_doctor_followup_booking/<int:doctor_booking_id>/', views.request_doctor_followup_booking, name='request_doctor_followup_booking'),
    path('aprove_doctor_followup_booking/<int:followup_booking_id>/', views.aprove_doctor_followup_booking, name='aprove_doctor_followup_booking'),
    path('doctor_followup_booking_detail/<int:pk>/', views.doctor_followup_booking_detail, name='doctor_followup_booking_detail'),
    path('request_zoom_meeting/<int:followup_booking_id>/', views.request_zoom_meeting, name='request_zoom_meeting'),
    path('approve_zoom_meeting/<int:zoom_booking_id>/', views.approve_zoom_meeting, name='approve_zoom_meeting'),

    path('followup_up_booking_request_list/', views.followup_up_booking_request_list, name='followup_up_booking_request_list'),
    path('zoom_meeting_request_list/', views.zoom_meeting_request_list, name='zoom_meeting_request_list'),

    path('all_follow_up_schedules/<int:booking_id>/', views.all_follow_up_schedules, name='all_follow_up_schedules'),
    path('all_follow_up_zoom_schedules/<int:booking_id>/', views.all_follow_up_zoom_schedules, name='all_follow_up_zoom_schedules'),


    path('create-patient-profile/', views.create_patient_profile, name='create_patient_profile'),
    path('create_medicine/', views.manage_medicine, name='create_medicine'),
    path('update_medicine/<int:id>/', views.manage_medicine, name='update_medicine'),
    path('delete_medicine/<int:id>/', views.delete_medicine, name='delete_medicine'),

    path('create_lab_test/', views.manage_lab_test, name='create_lab_test'),
    path('update_lab_test/<int:id>/', views.manage_lab_test, name='update_lab_test'),
    path('delete_lab_test/<int:id>/', views.delete_lab_test, name='delete_lab_test'),


    
    path('initiate_ai_prescription_payment/', views.initiate_ai_prescription_payment, name='initiate_ai_prescription_payment'),
    path('initiate_book_doctor_direct_payment/<int:doctor_id>/', views.initiate_book_doctor_direct_payment, name='initiate_book_doctor_direct_payment'),
    path('initiate_confirm_booking_payment/<int:prescription_id>/<int:doctor_id>/', views.initiate_confirm_booking_payment, name='initiate_confirm_booking_payment'),

    path('initiate_video_call_payment/<int:booking_id>/', views.initiate_video_call_payment, name='initiate_video_call_payment'),
    path('initiate_doctor_followup_booking_payment/<int:doctor_booking_id>/', views.initiate_doctor_followup_booking_payment, name='initiate_doctor_followup_booking_payment'),
    path('initiate_followup_video_consultation_payment/<int:followup_booking_id>/', views.initiate_followup_video_consultation_payment, name='initiate_followup_video_consultation_payment'),
    
    # path('translate/', views.translate_text, name='translate_text'),



    path('about/', views.about_us, name='about_us'),
    path('contact/', views.contact_us, name='contact_us'),



]

