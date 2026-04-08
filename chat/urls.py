from django.urls import path
from . import views


app_name = 'chat' 


urlpatterns = [
    path('chat/thread/<int:thread_id>/messages/', views.chat_thread_messages, name='chat_thread_messages'),
    path("<int:thread_id>/", views.chat_view, name="chat_view"),

    path("start_chat/<int:doctor_id>/", views.start_chat, name="start_chat"),

    path("doctor_chat_view/<int:patient_id>/", views.doctor_chat_view, name="doctor_chat_view"),
    path("patient_chat_view/<int:doctor_id>/", views.patient_chat_view, name="patient_chat_view"),
    
    path('doctor_notifications_view/', views.doctor_notifications_view, name='doctor_notifications_view'),
    path('patient_notifications_view/', views.patient_notifications_view, name='patient_notifications_view'),
    
    path("doctor/thread/<int:thread_id>/", views.doctor_chat_thread_view, name="doctor_chat_thread_view"),
    path("patient/thread/<int:thread_id>/", views.patient_chat_thread_view, name="patient_chat_thread_view"),
   
    path("send/<int:thread_id>/", views.send_message, name="send_message"),
    path('save-token/', views.save_device_token, name='save_device_token'),
    path('send-push/', views.send_push_to_doctor, name='send_push'),

   path("online_doctors_view/", views.online_doctors_view, name="online_doctors_view"),
   path("online_patients_view/", views.online_patients_view, name="online_patients_view"),

   path("group_conference/", views.group_conference, name="group_conference"),
   path("group_conference/<str:room_id>/", views.group_conference, name="group_conference_id"),

    path("create_meeting/", views.create_meeting, name="create_meeting"),
    path("invite/<int:room_id>/", views.invite_user, name="invite_user"),
    path("join/<str:invite_token>/", views.join_meeting_from_invite, name="join_meeting"),
    path("meeting/<int:room_id>/", views.meeting_room, name="meeting_room"),
   

   path("send_doctor_ringtone/<int:doctor_id>/", views.send_doctor_ringtone, name="send_doctor_ringtone"),

]
