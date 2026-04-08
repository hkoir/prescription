
import firebase_admin
from firebase_admin import credentials, messaging
from chat.models import DeviceToken  

import os
CRED_PATH = "/home/humayun/myproject/credentials/serviceAccountKey.json"


if not firebase_admin._apps:
    cred = credentials.Certificate(CRED_PATH)
    firebase_admin.initialize_app(cred)

def send_fcm_notification(user, title, body):  
    try:
        device = DeviceToken.objects.get(user=user)
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=device.token
        )
        response = messaging.send(message)
        print(f"Notification sent: {response}")
        return response
    except DeviceToken.DoesNotExist:
        print(f"[FCM] No device token found for user: {user}")
    except Exception as e:
        print(f"[FCM] Error sending notification: {e}")


# exam of usage
# from utils.fcm import send_fcm_notification
# send_fcm_notification(user, "New Message", "You have a new message.")
