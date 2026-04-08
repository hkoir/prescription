from django.shortcuts import render, get_object_or_404, redirect
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)
from django.core.cache import cache
from django.utils import timezone
from channels.db import database_sync_to_async


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        tenant_prefix = getattr(self.scope.get("tenant"), "schema_name", "public")
        scheme = self.scope.get("scheme", "ws")
        server = self.scope.get("server", ("unknown", 0))
        host, port = server
        path = self.scope.get("path", "/")
        query_string_bytes = self.scope.get("query_string", b"")
        query_string = query_string_bytes.decode("utf-8")
        url = f"{scheme}://{host}"
        if port and port not in (80, 443):
            url += f":{port}"
        url += path
        if query_string:
            url += f"?{query_string}"

        if user.is_anonymous:
            logger.info(f"Callconsumer WebSocket connection rejected: anonymous user tried to connect to {url}")
            await self.close()
            return
        if user.is_authenticated:
            cache.set(f"user_online_{user.id}", True, timeout=120)
            await self.set_online_status(user, True)

        self.group_name = f"{tenant_prefix}_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"Callconsumer WebSocket connected: user_id={user.id}, tenant={tenant_prefix}, group={self.group_name}, url={url}")

    async def disconnect(self, close_code):
        user = self.scope["user"]
        if user.is_authenticated:
            cache.delete(f"user_online_{user.id}")
            await self.set_online_status(user, False)
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"Callconsumer  WebSocket disconnected: user_id={self.scope['user'].id}, group={self.group_name}, close_code={close_code}")
        except Exception as e:
            logger.error(f" callconsumer Error during disconnect cleanup for user_id={self.scope['user'].id if self.scope.get('user') else 'unknown'}: {e}")



    async def incoming_call(self, event):
        logger.info(f"callconsumer Incoming call event received: {event}")
        try:
            await self.send(text_data=json.dumps({
                "type": "incoming_call",
                "caller_name": event.get("caller_name", "Unknown"),
                "zoom_start_url": event.get("zoom_start_url"),
                "zoom_join_url": event.get("zoom_join_url"),
            }))

            logger.debug("callconsumer Sent incoming_call message to client.")
        except Exception as e:
            logger.error(f"callconsumer Error sending incoming_call message: {e}")



    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            logger.warning("callconsumer Received empty WebSocket message.")
            return
        try:
            data = json.loads(text_data)
        except Exception as e:
            logger.error(f" callconsumer Failed to parse JSON message: {e}")
            return

        msg_type = data.get("type")
        logger.info(f"callconsumer Received message of type '{msg_type}' from user_id={self.scope['user'].id}")

        if msg_type == "ping":
            try:
                await self.send(text_data=json.dumps({"type": "pong"}))
                logger.debug("callconsumer Responded with pong to ping message.")
            except Exception as e:
                logger.error(f"callconsumer Error sending pong message: {e}")

        if msg_type == "doctor.joined":
            await self.doctor_joined(data)



    async def chat_message(self, event):
        logger.info(f"callconsumer chat_message event received: sender_id={event.get('sender_id')}, thread_id={event.get('thread_id')}")
        try:
            await self.send(text_data=json.dumps({
                "type": "chat_notify",
                "sender_id": event["sender_id"],
                "sender_name": event["sender_name"],
                "preview": event["message"][:80],
                "thread_id": event["thread_id"],
                "sent_at": event["sent_at"],
            }))
            logger.debug("callconsumer Sent chat_notify message to client.")
        except Exception as e:
            logger.error(f"callconsumer Error sending chat_notify message: {e}")



    async def chat_notify(self, event):
        logger.info(f"callconsumer chat_notify event received: {event}")
        try:
            await self.send(text_data=json.dumps({
                "type": "chat_message",
                "sender_name": event.get("sender_name"),
                "preview": event.get("preview", ""),
                "thread_id": event.get("thread_id"),
                "sent_at": event.get("sent_at"),
                "notification": "You have unread messages",
            }))
            logger.debug("callconsumer Sent chat_message notification to client.")
        except Exception as e:
            logger.error(f"callconsumer Error sending chat_message notification: {e}")



    async def doctor_joined(self, data):
        patient_id = data["patient_id"]
        tenant_prefix = self.scope["url_route"]["kwargs"].get("tenant_prefix", "unknown")

        await self.channel_layer.group_send(
            f"{tenant_prefix}_user_{patient_id}",
            {
                "type": "doctor_joined_message",
                "doctor_name": self.scope["user"].get_full_name(),
                "message": "Doctor has joined the call"
            }
        )

    async def doctor_joined_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "doctor.joined",
            "message": event["message"],
            "doctor_name": event["doctor_name"]
        }))

    async def play_ringtone(self, event):
        await self.send(text_data=json.dumps({
            "type": "play_ringtone",
            "from_user_id": event["from_user_id"],
            "caller_name": event["caller_name"],
            "webrtc_room": event.get("webrtc_room")  # forward room ID
        }))

     


    @database_sync_to_async
    def set_online_status(self, user, status):
        user.is_online = status
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])
