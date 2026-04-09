import json
import redis.asyncio as redis

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import ChatThread, ChatMessage
from prescription.models import Patient, Doctor
from django.utils import timezone
User = get_user_model()
REDIS_ONLINE_KEY = "chat:online_users"
import logging
logger = logging.getLogger(__name__)


# -----------------------------
# Redis Online Tracking Helpers
# -----------------------------

async def get_redis_connection():
    return redis.from_url("redis://127.0.0.1:6379", encoding="utf-8", decode_responses=True)

async def mark_online(user_id, key=REDIS_ONLINE_KEY):
    r = await get_redis_connection()
    await r.sadd(key, user_id)

async def mark_offline(user_id, key=REDIS_ONLINE_KEY):
    r = await get_redis_connection()
    await r.srem(key, user_id)

async def get_online_users(key=REDIS_ONLINE_KEY):
    r = await get_redis_connection()
    return await r.smembers(key)


# -----------------------------
# Chat Consumer
# -----------------------------

from django.core.cache import cache


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope["user"]
            if self.user.is_anonymous:
                logger.warning("chatconsumer WebSocket denied: anonymous user.")
                await self.close()
                return

            # Mark user online
            if self.user.is_authenticated:
                await self.set_user_online()

            self.tenant_prefix = self.scope["url_route"]["kwargs"].get("tenant_prefix", "unknown")
            self.user_id = int(self.scope["url_route"]["kwargs"]["user_id"])
            # self.user_id = self.scope["user"].id
            self.group_name = f"{self.tenant_prefix}_user_{self.user_id}"

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            logger.info(f"chatconsumer User {self.user.username} joined group: {self.group_name}")

            await self.accept()
            logger.info(f"chatconsumer WebSocket connected: user_id={self.user.id}, tenant={self.tenant_prefix}")
        except Exception as e:
            logger.exception("chatconsumer WebSocket connect error:")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.user.is_authenticated:
                await self.set_user_offline()

                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(f"chatconsumer WebSocket disconnected: user_id={self.user.id}, code={close_code}")
        except Exception as e:
            logger.exception("chatconsumer Error during WebSocket disconnect:")


    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            logger.warning("chatconsumer Empty WebSocket message received.")
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning("chatconsumer Invalid JSON received.")
            return

        msg = (data.get("message") or "").strip()
        to_id = data.get("to_user_id") or data.get("recipient_id")
        thread_id = data.get("thread_id")

        if not msg or not to_id:
            logger.warning("chatconsumer Missing message or recipient.")
            return

        try:
            to_id = int(to_id)
            sender = self.scope["user"]
            recipient = await database_sync_to_async(User.objects.get)(pk=to_id)
        except Exception as e:
            logger.exception(f"chatconsumer Failed to get recipient with id={to_id}")
            return

        try:
            if thread_id:
                try:
                    thread = await self._get_thread_by_id(thread_id)
                    created = False
                except ChatThread.DoesNotExist:
                    logger.warning(f"chatconsumer Thread id={thread_id} does not exist. Creating new thread.")
                    thread, created = await self._get_or_create_thread_for_pair(sender, recipient)
            else:
                thread, created = await self._get_or_create_thread_for_pair(sender, recipient)

            if created and sender.id != recipient.id:
                await self.channel_layer.group_send(
                    f"{self.tenant_prefix}_user_{recipient.id}",
                    {
                        "type": "incoming_chat_notification",
                        "from_user_id": sender.id,
                        "from_user_name": sender.get_full_name() or sender.username,
                        "thread_id": thread.id,
                    },
                )
                logger.info(f"chatconsumer New thread created between sender={sender.id} and recipient={recipient.id}")

            chat_message = await self._save_message(thread, sender, msg)

            payload = {
                "type": "chat_message",
                "message": msg,
                "sender_id": sender.id,
                "sender_name": sender.get_full_name() or sender.username,
                "thread_id": thread.id,
                "sent_at": chat_message.sent_at.isoformat(),
                "media_url": None,
            }

            await self.channel_layer.group_send(f"{self.tenant_prefix}_user_{recipient.id}", payload)

            if sender.id != recipient.id:
                await self.channel_layer.group_send(
                    f"{self.tenant_prefix}_user_{recipient.id}",
                    {
                        "type": "chat_notify",
                        "sender_name": sender.get_full_name() or sender.username,
                        "sender_id": sender.id,
                        "preview": msg[:80],
                        "thread_id": thread.id,
                        "sent_at": chat_message.sent_at.isoformat(),
                        "notification": "You have unread messages",
                    },
                )

            logger.debug(f" chatconsumer Message sent from user_id={sender.id} to user_id={recipient.id}: '{msg[:50]}'")

        except Exception as e:
            logger.exception("Error processing WebSocket message:")

   
   
    async def chat_message(self, event):
        thread_id = event["thread_id"]
        sender_id = event["sender_id"]
        current_user = self.scope["user"]

        try:
            session = self.scope.get("session")
            active_thread_id = session.get("active_thread_id") if session else None

            if str(active_thread_id) == str(thread_id) and current_user.id != sender_id:
                await database_sync_to_async(
                    ChatMessage.objects.filter(
                        thread_id=thread_id,
                        sender_id=sender_id,
                        read_at__isnull=True
                    ).update
                )(read_at=timezone.now())

        except Exception as e:
            print("⚠️ session error (ignored):", e)

        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "sender_id": sender_id,
            "sender_name": event["sender_name"],
            "message": event["message"],
            "thread_id": thread_id,
            "sent_at": event["sent_at"],
            "media_url": event.get("media_url"),
        }))




    async def chat_notify(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_notify",
            "sender_name": event["sender_name"],
            "sender_id": event.get("sender_id"),
            "preview": event.get("preview", ""),
            "thread_id": event["thread_id"],
            "sent_at": event["sent_at"],
            "notification": event.get("notification"),
        }))



    async def incoming_call(self, event):
        await self.send(text_data=json.dumps({
            "type": "incoming_call",
            "from_user_id": event["from_user_id"],
            "from_user_name": event["caller_name"],
            # "thread_id": event["thread_id"],
        }))



    # -------------------------
    # Helper Methods
    # -------------------------

    @database_sync_to_async
    def set_user_online(self):
        cache.set(f"chat_room_online_{self.user.id}", True, timeout=None)  # optional timeout

    @database_sync_to_async
    def set_user_offline(self):
        cache.delete(f"chat_room_online_{self.user.id}")

    @database_sync_to_async
    def _get_thread_by_id(self, thread_id):
        return ChatThread.objects.get(pk=thread_id)

    @database_sync_to_async
    def _user_is_doctor(self, user_id):
        return Doctor.objects.filter(user_id=user_id).exists()

    @database_sync_to_async
    def _user_is_patient(self, user_id):
        return Patient.objects.filter(user_id=user_id).exists()

    @database_sync_to_async
    def _find_existing_thread(self, tenant_schema, u1_id, u2_id):
        return (ChatThread.objects
                .filter(tenant_schema=tenant_schema)
                .filter(
                    Q(doctor_user_id=u1_id, patient_user_id=u2_id) |
                    Q(doctor_user_id=u2_id, patient_user_id=u1_id)
                )
                .first())

    async def _get_or_create_thread_for_pair(self, u1, u2):
        tenant_schema = self.tenant_prefix

        existing = await self._find_existing_thread(tenant_schema, u1.id, u2.id)
        if existing:
            return existing, False

        u1_is_doc = await self._user_is_doctor(u1.id)
        u2_is_doc = await self._user_is_doctor(u2.id)

        if u1_is_doc and not u2_is_doc:
            doctor_user, patient_user = u1, u2
        elif u2_is_doc and not u1_is_doc:
            doctor_user, patient_user = u2, u1
        else:
            doctor_user, patient_user = (u1, u2) if u1.id < u2.id else (u2, u1)

        thread = await database_sync_to_async(ChatThread.objects.create)(
            tenant_schema=tenant_schema,
            doctor_user=doctor_user,
            patient_user=patient_user,
        )
        return thread, True

    @database_sync_to_async
    def _save_message(self, thread, sender, text):
        msg = ChatMessage.objects.create(
            thread=thread,
            sender=sender,
            text=text,
        )
        ChatThread.objects.filter(pk=thread.pk).update(last_message_at=msg.sent_at)
        return msg




class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user", None)
        if not self.user.is_authenticated:
            await self.close()
            return

        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.room_group_name = f"video_chat_{self.thread_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({"type": "connection", "message": "WebSocket connected ✅"}))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        data["sender_channel_name"] = self.channel_name

        # Relay to others in group except sender
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "signal_message",
                "data": data
            }
        )

    async def signal_message(self, event):
        data = event["data"]

        # Prevent echo back to sender
        if self.channel_name != data.get("sender_channel_name"):
            await self.send(text_data=json.dumps(data))



    async def join_room(self, event):
        room_id = event['room_id']
        user = self.scope["user"]
        # Add this doctor to the room group
        await self.channel_layer.group_add(f"room_{room_id}", self.channel_name)
        # Send back info so the doctor can initialize the WebRTC connection
        await self.send_json({
            "type": "room_joined",
            "room_id": room_id,
            "your_id": user.id
        })






import json


class GroupVideoConsumer(AsyncWebsocketConsumer): 
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"video_group_{self.room_id}"
        self.user = self.scope.get("user", None)
        if not self.user.is_authenticated:
            await self.close()
            return
    
        self.user_id = str(getattr(self.user, "id", None) or self.channel_name)  
        self.username = str(getattr(self.user, "username", None) or "Anonymous")

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
 
        await self.send(text_data=json.dumps({
            "type": "welcome",
            "user_id": self.user_id,
            "username": getattr(self.user, "username", "Anonymous")
        }))

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_joined",
                "user_id": self.user_id,
                "username": getattr(self.user, "username", "Anonymous"),
                "sender_channel_name": self.channel_name
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "user_left",
                "user_id": self.user_id,
                "username": self.username
            }
        )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        data = json.loads(text_data)
        msg_type = data.get("type")   
        data["from"] = self.user_id
        data["username"] = self.username

        if msg_type == "ready":
            # Broadcast roster_ping
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "roster_ping", "sender": self.user_id, "username": self.username}
            )
            return

        if msg_type in ("offer", "answer", "candidate"):
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "signal_message", "data": data}
            )
            return

    # ---- Group event handlers ----

    async def signal_message(self, event):
        data = event["data"]
        if data.get("from") == self.user_id:
            return
        await self.send(text_data=json.dumps(data))

 

    async def user_joined(self, event):  
        if self.channel_name != event.get("sender_channel_name", ""):
            await self.send(text_data=json.dumps({
                "type": "user_present",          
                "user_id": event["user_id"],      
                "username": event.get("username", "Anonymous")
            }))



    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            "type": "user_left",
            "user_id": event["user_id"],
            "username": event.get("username", "Anonymous")
        }))

  
    async def roster_ping(self, event):
        if event["sender"] == self.user_id:
            return
        await self.send(text_data=json.dumps({
            "type": "user_present",
            "user_id": event["sender"],        # <- initiator's ID
            "username": event["username"]      # <- initiator's username
        }))






    
