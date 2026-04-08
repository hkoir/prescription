import firebase_admin
import requests
import os
from firebase_admin import credentials, messaging




BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIREBASE_KEY_PATH = os.path.join(BASE_DIR, 'chat', 'firebase-key.json')

cred = credentials.Certificate(FIREBASE_KEY_PATH)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

    
def send_push_notification(token, title, body, path='', schema='public'):
    base_url = f"https://{schema}.aiha.live"
    full_url = f"{base_url}{path}"

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
        data={
            'click_action': 'FLUTTER_NOTIFICATION_CLICK',
            'url': full_url,
        }
    )

    try:
        response = messaging.send(message)
        print("✅ Push sent:", response)
        return response
    except Exception as e:
        print("❌ Push error:", e)
        return None



# doctor = appointment.doctor
# if doctor.fcm_token:
#     send_push_notification(
#         token=doctor.fcm_token,
#         title="New Appointment Booked",
#         body=f"Patient {appointment.patient.name} just booked you.",
#     )
# from chat.firebase_service import send_push_notification

# send_push_notification(
#     token="your_fcm_device_token_here",
#     title="New Message",
#     body="You have received a new chat message!",
# )
