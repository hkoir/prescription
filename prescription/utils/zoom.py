
import requests
from datetime import datetime, timedelta
import json
import logging
import time

ACCOUNT_ID = "8aNJbfonSkqZ6Wk5S6N6Ag"
CLIENT_ID = "_6eQ_OawTCCDXO02owBCwQ"
CLIENT_SECRET = "yZ9g153KTZzR8ELIbgnLToonxcW7Cj4H"


logger = logging.getLogger(__name__)

zoom_token_cache = {
    "access_token": None,
    "expires_at": 0
}

def get_zoom_access_token():
    current_time = time.time()
    if zoom_token_cache["access_token"] and current_time < zoom_token_cache["expires_at"]:
        return zoom_token_cache["access_token"]

    url = "https://zoom.us/oauth/token"
    payload = {
        "grant_type": "account_credentials",
        "account_id": ACCOUNT_ID,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(url, data=payload, headers=headers, auth=(CLIENT_ID, CLIENT_SECRET))
    response.raise_for_status()

    data = response.json()
    access_token = data["access_token"]
    expires_in = data["expires_in"]  # typically 3600 seconds (1 hour)

    # Update cache
    zoom_token_cache["access_token"] = access_token
    zoom_token_cache["expires_at"] = current_time + expires_in - 60  # subtract 60s buffer

    return access_token



def create_zoom_meeting(topic="Online Appointment", duration=30, timezone="UTC"):
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
        "timezone": timezone,
        "settings": {
            "join_before_host": True,
            "waiting_room": False,
            "host_video": True,
            "participant_video": True
        }
    }

    url = "https://api.zoom.us/v2/users/me/meetings"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()  # Includes 'join_url', 'start_url', etc.
    except requests.RequestException as e:
        logger.error("Failed to create Zoom meeting: %s", e)
        raise