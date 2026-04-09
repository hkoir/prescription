import firebase_admin
import os
from firebase_admin import credentials, messaging
from django.conf import settings


def get_firebase_app():
    if not firebase_admin._apps:
        key_path = os.path.join(settings.BASE_DIR, 'chat', 'firebase-key.json')

        if not os.path.exists(key_path):
            raise Exception(f"Firebase key not found at {key_path}")

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    return firebase_admin.get_app()


def send_push_notification(token, title, body, path='', schema='public'):
    try:
        get_firebase_app()

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

        response = messaging.send(message)
        print("✅ Push sent:", response)
        return response

    except Exception as e:
        print("❌ Push error:", e)
        return None