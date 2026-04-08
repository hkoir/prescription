from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Max, Count
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from prescription.models import Patient, Doctor, DoctorBooking, DoctorFolloupBooking
from .models import ChatThread, ChatMessage, DeviceToken, BoardRoom, BoardRoomInvite, BoardRoomParticipant
from .consumers import get_online_users
from chat.utils import send_push_notification
from accounts.utils import send_sms
from messaging.views import create_notification
from django.utils.timezone import now
import json
import uuid
from datetime import datetime
import chat.utils

User = get_user_model()


@login_required
def chat_thread_messages(request, thread_id):
    thread = get_object_or_404(ChatThread, pk=thread_id)
    if request.user != thread.doctor_user and request.user != thread.patient_user:
        return JsonResponse({"error": "Unauthorized"}, status=403)
    messages = thread.messages.order_by('sent_at').values(
        'id', 'sender_id', 'text', 'sent_at'
    )
    messages_list = list(messages)
    return JsonResponse({"messages": messages_list})



@login_required
def chat_view(request, thread_id):
    thread = get_object_or_404(ChatThread, pk=thread_id)
    # TODO: optional permission check: ensure request.user is doctor or patient in this thread
    return render(request, "chat/chat.html", {"thread": thread})




def _presence_key(schema_name="public"):
    return f"chat:{schema_name}:online_users"


def get_or_create_thread_for_doctor_patient_user(tenant_schema, doctor_user, patient_user, force_new=False):
    if not force_new:
        existing = ChatThread.objects.filter(
            tenant_schema=tenant_schema
        ).filter(
            Q(doctor_user=doctor_user, patient_user=patient_user) |
            Q(doctor_user=patient_user, patient_user=doctor_user)
        ).first()
        if existing:
            return existing, False

    # Create a fresh thread
    thread = ChatThread.objects.create(
        tenant_schema=tenant_schema,
        doctor_user=doctor_user,
        patient_user=patient_user,
    )
    return thread, True



# ------------------------------------------------------------------
# PATIENT starts / resumes chat with a doctor
# ------------------------------------------------------------------

def get_all_threads_for_user(user, tenant_schema):
    threads_qs = (
        ChatThread.objects
        .filter(tenant_schema=tenant_schema)
        .filter(Q(patient_user=user) | Q(doctor_user=user))
        .select_related('doctor_user', 'patient_user')
        .annotate(
            last_msg_at=Max('messages__sent_at'),
            unread_count=Count(
                'messages',
                filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender_id=user.id)
            ),
            read_count=Count(
                'messages',
                filter=Q(messages__read_at__isnull=False) & ~Q(messages__sender_id=user.id)
            ),
        )
        .order_by('-last_msg_at', '-created_at')
    )

    thread_list = []
    for t in threads_qs:
        if t.patient_user == user:
            partner = t.doctor_user

        else:
            partner = t.patient_user

        last_msg = t.messages.order_by('-sent_at').first()
        last_text = last_msg.text if last_msg else ""

        thread_list.append({
            "id": t.id,
            "partner_user": partner,
            "last_text": last_text,
            "unread_count": t.unread_count,
            "read_count": t.read_count,  # new added field
        })

    return thread_list


@login_required
def patient_chat_view(request, doctor_id):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    patient_user = request.user
    doctor_obj = get_object_or_404(Doctor, pk=doctor_id)
    doctor_user = doctor_obj.user   

    existing_thread = (
        ChatThread.objects
        .filter(tenant_schema=tenant_schema)
        .filter(
            Q(doctor_user=doctor_user, patient_user=patient_user) |
            Q(doctor_user=patient_user, patient_user=doctor_user)
        )
        .first()
    )

    if request.GET.get("new") == "1" and existing_thread:
        return redirect(reverse("chat:patient_chat_view", args=[doctor_id]))

    if existing_thread:
        thread = existing_thread
    else:
        thread = ChatThread.objects.create(
            tenant_schema=tenant_schema,
            doctor_user=doctor_user,
            patient_user=patient_user,
        )
    request.session["active_thread_id"] = str(thread.id)

    ChatMessage.objects.filter(
        thread=thread,
        read_at__isnull=True
    ).exclude(sender=patient_user).update(read_at=now())

    messages_qs = ChatMessage.objects.filter(thread=thread).select_related("sender").order_by("sent_at")
    all_threads = get_all_threads_for_user(request.user, tenant_schema)
    initial_messages = [
        {
            "sender_id": m.sender_id,
            "sender_name": m.sender.get_full_name() or m.sender.username,
            "text": m.text,
            "sent_at": m.sent_at,
            "media_url": m.media.url if m.media else None,
        }
        for m in messages_qs
    ]

    context = {
        "chat_partner": doctor_user,
        "chat_partner_id": doctor_user.id,
        "user_role": "patient",
        "user_id": patient_user.id,
        "tenant_prefix": tenant_schema,
        "thread_id": thread.id,
        "current_patient_user_id": patient_user.id,
        "current_thread_id": thread.id,
        "initial_messages": initial_messages,
        "all_threads": all_threads,
        "is_chat_open":True,
        'is_initiator': True, 
        'doctor':doctor_obj
    }
    return render(request, "chat/chat_room.html", context)


# ------------------------------------------------------------------
# DOCTOR opens chat with a patient (legacy URL) OR resumes via ?thread=
# ------------------------------------------------------------------


@login_required
def doctor_chat_view(request, patient_id):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    doctor_user = request.user

    patient_obj = get_object_or_404(Patient, pk=patient_id)
    patient_user = patient_obj.user  

    thread = (
        ChatThread.objects
        .filter(tenant_schema=tenant_schema)
        .filter(
            Q(doctor_user=doctor_user, patient_user=patient_user) |
            Q(doctor_user=patient_user, patient_user=doctor_user)
        )
        .first()
    )

    # If "new=1" but thread exists, redirect to existing one
    if request.GET.get("new") == "1" and thread:
        return redirect(reverse("chat:doctor_chat_view", args=[patient_id]))

    if not thread:
        thread = ChatThread.objects.create(
            tenant_schema=tenant_schema,
            doctor_user=doctor_user,
            patient_user=patient_user,
        )

    request.session["active_thread_id"] = str(thread.id)

    if doctor_user in (thread.doctor_user, thread.patient_user):
        thread.messages.filter(
            Q(read_at__isnull=True) & ~Q(sender=doctor_user)
        ).update(read_at=timezone.now())

    messages_qs = ChatMessage.objects.filter(thread=thread).select_related("sender").order_by("sent_at")
    all_threads = get_all_threads_for_user(request.user, tenant_schema)

    initial_messages = [
        {
            "sender_id": m.sender_id,
            "sender_name": m.sender.get_full_name() or m.sender.username,
            "text": m.text,
            "sent_at": m.sent_at,
            "media_url": m.media.url if m.media else None,
        }
        for m in messages_qs
    ]

    context = {
        "chat_partner": patient_user,
        "chat_partner_id": patient_user.id,
        "user_role": "doctor",
        "user_id": doctor_user.id,
        "tenant_prefix": tenant_schema,
        "thread_id": thread.id,
        "current_patient_user_id": patient_user.id,
        "current_thread_id": thread.id,
        "initial_messages": initial_messages,
        "all_threads": all_threads,
        "is_chat_open":True,
        'is_initiator': True, 
        'patient':patient_obj
    }
    return render(request, "chat/chat_room.html", context)



# ------------------------------------------------------------------
# DOCTOR (or participant) opens chat *by thread id* (canonical)
# ------------------------------------------------------------------

@login_required
def doctor_chat_thread_view(request, thread_id):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    doctor_user = request.user

    #thread = get_object_or_404(ChatThread, id=thread_id, doctor_user=request.user, tenant_schema=tenant_schema)
    thread = get_object_or_404(
        ChatThread.objects.filter(
            Q(id=thread_id),
            Q(doctor_user=request.user) | Q(patient_user=request.user),
            Q(tenant_schema=tenant_schema)
        )
    )
   
    thread.messages.filter(
        Q(read_at__isnull=True) & ~Q(sender=request.user)
    ).update(read_at=now())   

    if doctor_user.id not in (thread.doctor_user_id, thread.patient_user_id):
        return HttpResponseForbidden("You are not part of this chat thread.")
    ChatMessage.objects.filter(
        thread=thread,
        read_at__isnull=True
    ).exclude(sender=doctor_user).update(read_at=timezone.now())
    messages_qs = ChatMessage.objects.filter(thread=thread).select_related("sender").order_by("sent_at")

    initial_messages = [
        {
            "sender_id": m.sender_id,
            "sender_name": m.sender.get_full_name() or m.sender.username,
            "text": m.text,
            "sent_at": m.sent_at,
            "media_url": m.media.url if m.media else None,
        }
        for m in messages_qs
    ]

    # doctor_instance = Doctor.objects.get(user=doctor_user)

    if doctor_user.id == thread.doctor_user_id:
        chat_partner = thread.patient_user
    else:
        chat_partner = thread.doctor_user   
    all_threads = get_all_threads_for_user(request.user, tenant_schema)    
    patient_booking = DoctorBooking.objects.filter(patient__user=thread.patient_user).first()

    context = {
        "chat_partner": chat_partner,
        "chat_partner_id": chat_partner.id,
        "user_role": "doctor",
        "user_id": doctor_user.id,
        "tenant_prefix": tenant_schema,
        "thread_id": thread.id,
        "current_thread_id": thread.id,
        "initial_messages": initial_messages,
        "all_threads": all_threads,
        'patient_booking':patient_booking,
        'is_initiator': True, 
    }
    return render(request, "chat/chat_room.html", context)




@login_required
def patient_chat_thread_view(request, thread_id):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    patient_user = request.user
    #thread = get_object_or_404(ChatThread, id=thread_id, patient_user=request.user, tenant_schema=tenant_schema)
    thread = get_object_or_404(
        ChatThread.objects.filter(
            Q(id=thread_id),
            Q(doctor_user=request.user) | Q(patient_user=request.user),
            Q(tenant_schema=tenant_schema)
        )
    )
    thread.messages.filter(
        Q(read_at__isnull=True) & ~Q(sender=request.user)
    ).update(read_at=now())
    if patient_user.id not in (thread.doctor_user_id, thread.patient_user_id):
        return HttpResponseForbidden("You are not part of this chat thread.")

    messages_qs = ChatMessage.objects.filter(thread=thread).select_related("sender").order_by("sent_at")

    initial_messages = [
        {
            "sender_id": m.sender_id,
            "sender_name": m.sender.get_full_name() or m.sender.username,
            "text": m.text,
            "sent_at": m.sent_at,
            "media_url": m.media.url if m.media else None,
        }
        for m in messages_qs
    ]

    if patient_user.id == thread.patient_user_id:
        chat_partner = thread.doctor_user
    else:
        chat_partner = thread.patient_user

    all_threads = get_all_threads_for_user(request.user, tenant_schema)

    context = {
        "chat_partner": chat_partner,
        "chat_partner_id": chat_partner.id,
        "user_role": "patient",
        "user_id": patient_user.id,
        "tenant_prefix": tenant_schema,
        "thread_id": thread.id,
        "current_thread_id": thread.id,
        "initial_messages": initial_messages,
        "all_threads": all_threads,
        'is_initiator': True, 
    }
    return render(request, "chat/chat_room.html", context)

# ------------------------------------------------------------------
# DOCTOR notifications list (active/inactive = unread_count>0)
# ------------------------------------------------------------------


@login_required
def doctor_notifications_view(request):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    user = request.user
    threads_qs = (
        ChatThread.objects
        .filter(tenant_schema=tenant_schema)
        .filter(Q(patient_user=user) | Q(doctor_user=user))
        .select_related('doctor_user', 'patient_user')
        .annotate(
            last_msg_at=Max('messages__sent_at'),
            unread_count=Count(
                'messages',
                filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)
            )
        )
        .order_by('-last_msg_at', '-created_at')
    )
    patient_user_ids = [t.patient_user_id for t in threads_qs]

    patient_map = {
        p.user_id: p.pk
        for p in Patient.objects.filter(user_id__in=patient_user_ids)
    }

 
    thread_rows = []
    for t in threads_qs:
        if t.doctor_user == user:
            partner = t.patient_user
        else:
            partner = t.doctor_user  
        last_msg = t.messages.order_by('-sent_at').first()
        last_text = last_msg.text if last_msg else ""
        continue_chat_url = reverse('chat:doctor_chat_thread_view', args=[t.id])
        patient_pk = patient_map.get(t.patient_user_id)     

        if patient_pk is not None:
            new_chat_url = f"{reverse('chat:doctor_chat_view', args=[patient_pk])}?new=1"
        else:
            new_chat_url = f"{continue_chat_url}?new=1"

        thread_rows.append({
            "thread": t,
            "partner_user": partner,
            "unread_count": t.unread_count,
            "last_text": last_text,
            "continue_chat_url": continue_chat_url,
            "new_chat_url": new_chat_url,
            "thread_exists": bool(t.id),
          
        })

    context = {
        "thread_rows": thread_rows,
        "tenant_prefix": tenant_schema,
        "doctor_user_id": user.id,
    }
    return render(request, "chat/doctor_notifications.html", context)



@login_required
def patient_notifications_view(request):
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    user = request.user

    threads_qs = (
        ChatThread.objects
        .filter(tenant_schema=tenant_schema)
        .filter(Q(patient_user=user) | Q(doctor_user=user))
        .select_related('doctor_user', 'patient_user')
        .annotate(
            last_msg_at=Max('messages__sent_at'),
            unread_count=Count(
                'messages',
                filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)
            )
        )
        .order_by('-last_msg_at', '-created_at')
    )

    doctor_user_ids = [t.doctor_user_id for t in threads_qs]

    doctor_map = {
        d.user_id: d.pk
        for d in Doctor.objects.filter(user_id__in=doctor_user_ids)
    }


    thread_rows = []
    for t in threads_qs:
        doctor_user = t.doctor_user
        last_msg = t.messages.order_by('-sent_at').first()
        last_text = last_msg.text if last_msg else ""

        continue_chat_url = reverse('chat:patient_chat_thread_view', args=[t.id])
        doctor_pk = doctor_map.get(t.doctor_user_id)       

        if doctor_pk is not None:
            new_chat_url = f"{reverse('chat:patient_chat_view', args=[doctor_pk])}?new=1"
        else:
            new_chat_url = f"{continue_chat_url}?new=1"

        thread_rows.append({
            "thread": t,
            "doctor_user": doctor_user,
            "unread_count": t.unread_count,
            "last_text": last_text,
            "continue_chat_url": continue_chat_url,
            "new_chat_url": new_chat_url,
            "thread_exists": bool(t.id),
        
        })

    context = {
        "thread_rows": thread_rows,
        "tenant_prefix": tenant_schema,
        "patient_user_id": user.id,
    }
    return render(request, "chat/patient_notifications.html", context)



@csrf_exempt
def save_device_token(request):
    data = json.loads(request.body)
    token = data.get("token")

    if request.user.is_authenticated:
        DeviceToken.objects.update_or_create(user=request.user, defaults={'token': token})
        return JsonResponse({"status": "saved"})
    return JsonResponse({"error": "unauthenticated"}, status=401)



@csrf_exempt
def send_push_to_doctor(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            doctor_id = data.get("doctor_id")
            action = data.get("action")

            doctor = User.objects.get(id=doctor_id)
            fcm_token = doctor.fcm_token

            if not fcm_token:
                return JsonResponse({"error": "Doctor FCM token missing"}, status=400)

            title = "New Patient Action"
            body = f"A patient started a {'chat' if action == 'chat' else 'video call'} session with you."

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                token=fcm_token
            )

            response = messaging.send(message)
            return JsonResponse({"message_id": response})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)




@login_required
@require_POST
def send_message(request, thread_id):
    thread = get_object_or_404(ChatThread, pk=thread_id)   

    text = (request.POST.get('text') or '').strip()
    media_file = request.FILES.get('media')

    if not text and not media_file:
        return JsonResponse({"error": "Empty message."}, status=400)

    msg = ChatMessage.objects.create(
        thread=thread,
        sender=request.user,
        text=text or "",
        media=media_file,
    )  

    thread.last_message_at = msg.sent_at
    thread.save(update_fields=["last_message_at"])

    sender_id = request.user.id
    if thread.doctor_user_id == sender_id:
        recipient_id = thread.patient_user_id
    else:
        recipient_id = thread.doctor_user_id
    tenant_schema = getattr(request.tenant, "schema_name", "public")
    tenant_prefix =  tenant_schema
    group_sender = f"{tenant_prefix}_user_{sender_id}"
    group_recipient = f"{tenant_prefix}_user_{recipient_id}"
    channel_layer = get_channel_layer()

    payload = {
        "type": "chat_message",
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "sender_name": request.user.get_full_name() or request.user.username,
        "message": msg.text or "",
        "media_url": msg.media.url if msg.media else None,
        "thread_id": thread.id,
        "sent_at": msg.sent_at.isoformat(),
    }

    async_to_sync(channel_layer.group_send)(group_sender, payload)
    async_to_sync(channel_layer.group_send)(group_recipient, payload)

    notification_payload = {
        "type": "chat_notify",
        "sender_id": sender_id,
        "sender_name": request.user.get_full_name() or request.user.username,
        "preview": msg.text[:80] if msg.text else "📎 Media file",
        "thread_id": thread.id,
        "sent_at": msg.sent_at.isoformat(),
        "notification": "New message received",
    }

    if recipient_id != sender_id:
        async_to_sync(channel_layer.group_send)(group_recipient, notification_payload)

    return JsonResponse({
        "id": msg.id,
        "sender": payload["sender_name"],
        "sender_id": sender_id,
        "text": msg.text or "",
        "media_url": payload["media_url"],
        "sent_at": msg.sent_at.strftime("%Y-%m-%d %H:%M"),
    })


def online_patients_view(request):
    online_ids = async_to_sync(get_online_users)()
    print("ONLINE IDS (raw):", online_ids, type(online_ids))
    patients = User.objects.filter(id__in=online_ids, role="patient")
    print("PATIENT QS COUNT:", patients.count())
    return render(request, "chat/online_patients.html", {"patients": patients})


def online_doctors_view(request):
    online_ids = async_to_sync(get_online_users)()
    print("ONLINE IDS (raw):", online_ids, type(online_ids))
    doctors = User.objects.filter(id__in=online_ids, role="doctor")
    print("DOCTOR QS COUNT:", doctors.count())
    return render(request, "chat/online_doctors.html", {"doctors": doctors})





@login_required
def start_chat(request, doctor_id):
    from chat.models import ChatThread
    from accounts.models import CustomUser
    doctor_user = CustomUser.objects.get(id=doctor_id)
    tenant = request.tenant.schema_name
    thread, created = ChatThread.objects.get_or_create(
        tenant_schema=tenant,
        doctor_user=doctor_user,
        patient_user=request.user,
    )
    return redirect('chat:chat_view', thread_id=thread.id)


import logging
logger = logging.getLogger(__name__)


def group_conference(request, room_id=None):
    booking = None
    booking_obj = None
    patient_info = None
    doctor_info = None
    followup_bookings = None
   

    # Check if this user is a Patient
    if request.user.role == 'patient':
        patient = request.user.patient_profile   
        booking = DoctorBooking.objects.filter(
            webrtc_room=room_id,
            patient=patient
        ).first()
        logger.info(f"Detected patient: {patient.id}, booking={booking}")

    elif request.user.role == 'doctor':
        doctor = Doctor.objects.get(user=request.user)      
        booking = DoctorBooking.objects.filter(
            webrtc_room=room_id,
            doctor=doctor
        ).first()

        if not booking:
            booking = DoctorBooking.objects.filter(
                webrtc_room=room_id
            ).first()
            
        logger.info(f"Detected doctor: {doctor.id}, booking={booking}")


    elif request.user.role == 'staff':
        booking = DoctorBooking.objects.filter(
            webrtc_room=room_id
        ).first() 
        logger.info(f"Staff user {request.user.id} attending room {room_id}, booking={booking}")

    else:
        role = "unknown"
        logger.info("User has no patient_profile or doctor → unknown role.")
       
    if booking:
        patient_info = {
            "id": booking.patient.id,
            "name": booking.patient.user.username,
            "email": booking.patient.user.email,
            "phone": booking.patient.phone,
        }
        doctor_info = {
            "id": booking.doctor.id,
            "name": booking.doctor.full_name,
            "email": booking.doctor.user.email if booking.doctor.user else None,
            "phone": booking.doctor.phone,
        }
        followup_bookings = booking.doctor_folloup_bookings.all()

    return render(request, "chat/group_conference.html", {
        "room_id": room_id,
        "patient_info": patient_info,
        "doctor_info": doctor_info,
        "booking": booking,
        "followup_bookings": followup_bookings,
      
    })


@login_required
def create_meeting(request):
    if request.method == "POST":
        title = request.POST.get("title", "")
        host_name = request.POST.get("host_name", request.user.get_full_name() or request.user.username)
        start_time_str = request.POST.get("start_time", "")

        try:           
            start_time = timezone.make_aware(datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M"))
        except Exception:
            start_time = timezone.now() 
        room = BoardRoom.objects.create(
            title=title,
            host=request.user,
            host_name=host_name,
            start_time=start_time
        )
        return redirect("chat:invite_user", room_id=room.id)
    return render(request, "chat/group_video/create_meeting.html")


import re
@login_required
def invite_user(request, room_id):
    room = get_object_or_404(BoardRoom, id=room_id)
    
    if request.method == "POST":
        emails_raw = request.POST.get("emails")  # changed field name to "emails"
        if not emails_raw:
            messages.error(request, "Please enter at least one email.")
            return redirect("chat:invite_user", room_id=room.id)
        emails = [e.strip() for e in re.split(r"[;,]", emails_raw) if e.strip()]
        invite_links = []
        for email in emails:
            invite_token = str(uuid.uuid4())
            invite = BoardRoomInvite.objects.create(
                room=room,
                invited_by=request.user,
                email=email,
                invite_token=invite_token
            )
            link = request.build_absolute_uri(f"/chat/join/{invite.invite_token}/")
            invite_links.append(link)
            send_mail(
                subject=f"Meeting Invitation: {room.title}",
                message=(
                    f"You are invited to join the meeting.\n\n"
                    f"Host: {room.host_name}\n"
                    f"Meeting Time: {room.start_time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Meeting Title: {room.title}\n"
                    f"Join Link: {link}\n\n"
                    f"Please do not share this link."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True
            )
        return render(request, "chat/group_video/invite_sent.html", {"invite_links": invite_links, "room": room})
    return render(request, "chat/group_video/invite_user.html", {"room": room})


def join_meeting_from_invite(request, invite_token):
    invite = get_object_or_404(BoardRoomInvite, invite_token=invite_token)
    invite.accepted = True
    invite.save()
    if request.user.is_authenticated:
        BoardRoomParticipant.objects.get_or_create(room=invite.room, user=request.user)
    else:
        BoardRoomParticipant.objects.create(room=invite.room, name=f"Guest-{invite.email}")
    return redirect("chat:meeting_room", room_id=invite.room.id)



def meeting_room(request, room_id):
    room = get_object_or_404(BoardRoom, id=room_id)    
    if request.user.is_authenticated:
        BoardRoomParticipant.objects.get_or_create(room=room, user=request.user)
    else:
        name = request.GET.get("name") or f"Guest-{room_id}"
        BoardRoomParticipant.objects.get_or_create(room=room, name=name)
    return render(request, "chat/group_video/group_conference.html", {
        "room": room,
        "room_id": room.room_id,  
        "host_name": room.host_name,
        "start_time": room.start_time
    })



@login_required
@csrf_exempt 
def send_doctor_ringtone(request, doctor_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method."})
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    if not doctor.user:
        return JsonResponse({"success": False, "error": "Doctor has no associated user."})      
    doctor_user = doctor.user
    fcm_token = getattr(doctor_user, 'fcm_token', None) if doctor_user else None

    booking = DoctorBooking.objects.filter(
        patient=request.user.patient_profile,
        doctor=doctor,
        status="pending"  
    ).first()

    if not booking:
        return JsonResponse({"success": False, "error": "No active booking found."})
    webrtc_room = booking.webrtc_room
    caller_name = (
        getattr(getattr(request.user, "patient_profile", None), "full_name", None)
        or request.user.get_full_name()
        or request.user.username
    )

    tenant_prefix = getattr(getattr(request, "tenant", None), "schema_name", "public")
    group_name = f"{tenant_prefix}_user_{doctor.user.id}"
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "play_ringtone",
            "from_user_id": request.user.id,
            "caller_name": caller_name,
            "webrtc_room": webrtc_room,  # send room info here
        }
    )
    message = f"Your Patient {request.user.username} is trying to make a video call for consulation Please Enter into conference room."
    send_sms(tenant=request.tenant, phone_number=doctor.phone, message=message)
    create_notification(request.user, notification_type='Doctor booking msg', message=message,  patient=request.user.patient_profile, doctor=doctor)
    if fcm_token:
        send_push_notification(
                token=fcm_token,
                title="New Appointment",
                body="You have a new appointment request.",
                path="/finance/doctor/dashboard/",
                schema=request.tenant.schema_name
            )     
    return JsonResponse({"success": True, "message": "Ringtone sent"})
