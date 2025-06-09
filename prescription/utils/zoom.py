# utils/zoom.py
import requests
from datetime import datetime, timedelta
import json

ACCOUNT_ID = "8aNJbfonSkqZ6Wk5S6N6Ag"
CLIENT_ID = "_6eQ_OawTCCDXO02owBCwQ"
CLIENT_SECRET = "yZ9g153KTZzR8ELIbgnLToonxcW7Cj4H"



def get_zoom_access_token():
    url = "https://zoom.us/oauth/token"
    payload = {
        "grant_type": "account_credentials",
        "account_id": ACCOUNT_ID,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Zoom requires client_id and client_secret as Basic Auth
    response = requests.post(url, data=payload, headers=headers, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()

    return response.json()["access_token"]


def create_zoom_meeting(topic="Online Appointment", duration=30):
    access_token = get_zoom_access_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    start_time = (datetime.utcnow() + timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "topic": topic,
        "type": 2,  # Scheduled meeting
        "start_time": start_time,
        "duration": duration,
        "timezone": "UTC",
        "settings": {
            "join_before_host": True,
            "waiting_room": False
        }
    }

    url = "https://api.zoom.us/v2/users/me/meetings"
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()

    return response.json()  # Returns dict with 'join_url', 'start_url', etc.
