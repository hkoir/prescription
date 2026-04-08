from django.shortcuts import render,redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import AllowAny
from django.db import IntegrityError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db.models import Q

from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import IntegrityError
from django_tenants.utils import schema_context, get_tenant_model
from accounts.models import CustomUser  # use your custom user model
from clients.models import Client  # your tenant model
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
import jwt
import datetime
import jwt
from django.http import HttpResponseBadRequest
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from prescription.models import Doctor
from rest_framework.views import APIView

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    data = request.data
    tenant_schema = data.get("tenant", "prescription")
    Tenant = get_tenant_model()

    try:
        tenant_obj = Tenant.objects.get(schema_name=tenant_schema)
    except Tenant.DoesNotExist:
        return Response({"error": f"Tenant '{tenant_schema}' does not exist"}, status=400)

    username = data.get("username")
    phone = data.get("phone_number")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "patient")

    if not all([username, phone, email, password]):
        return Response({"error": "All fields are required"}, status=400)

    try:
        with schema_context(tenant_schema):
            # Check for duplicates
            if CustomUser.objects.filter(username=username).exists():
                return Response({"error": "Username already exists"}, status=400)

            if CustomUser.objects.filter(email=email).exists():
                return Response({"error": "Email already exists"}, status=400)

            if CustomUser.objects.filter(phone_number=phone).exists():
                return Response({"error": "Phone number already exists"}, status=400)

            # Create the user
            user = CustomUser.objects.create_user(
                username=username,
                phone_number=phone,
                email=email,
                password=password,
                role=role,
                tenant=tenant_obj
            )
            return Response({"message": "Signup successful"}, status=201)

    except IntegrityError as e:
        return Response({"error": "Integrity error: " + str(e)}, status=400)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"error": "Internal server error", "details": str(e)}, status=500)



#########################################################
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'] = serializers.CharField(required=True)
        self.fields['password'] = serializers.CharField(required=True)
        self.fields['tenant'] = serializers.CharField(required=True)

    def validate(self, attrs):
        tenant_schema = self.context['request'].data.get('tenant')
        if not tenant_schema:
            raise serializers.ValidationError('Tenant is required.')

        identifier = attrs.get('username')
        password = attrs.get('password')

        with schema_context(tenant_schema):
            user = CustomUser.objects.filter(
                Q(username=identifier) | Q(email=identifier) | Q(phone_number=identifier)
            ).first()

            if user is None or not user.check_password(password):
                raise serializers.ValidationError('Invalid credentials.')

            if not user.is_active:
                raise serializers.ValidationError('User account is inactive.')

            # Dynamically map to the correct field so JWT can work
            if user.phone_number == identifier:
                self.username_field = 'phone_number'
            elif user.email == identifier:
                self.username_field = 'email'
            else:
                self.username_field = 'username'

            attrs[self.username_field] = getattr(user, self.username_field)

            return super().validate(attrs)



class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)




from django.http import HttpResponseBadRequest




@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_fcm_token(request):
    token = request.data.get("fcm_token")
    tenant_schema = request.data.get("tenant", "prescription")  # default tenant for testing
    if not token:
        return Response({"error": "No token"}, status=400)

    with schema_context(tenant_schema):
        request.user.fcm_token = token
        request.user.save()
        return Response({"message": "Token saved"})





def generate_auto_login_token(user):
    now = timezone.now()
    payload = {
        'user_id': user.id,
        'exp': int((now + datetime.timedelta(minutes=55)).timestamp()),  # 5 min expiry
        'iat': int(now.timestamp()),
        'type': 'auto-login',
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_auto_login_token(request):
    token = generate_auto_login_token(request.user)
    # Return the auto-login URL with the token as query parameter
    return JsonResponse({
        'auto_login_url': f"https://prescription.aiha.live/mobile_api/auto-login-view/?token={token}"
    })


from django.contrib.auth import login, get_backends
DOCTOR_ROLE_VALUE = 'doctor' 

def _is_doctor(user) -> bool:
    role = getattr(user, 'role', None)
    return isinstance(role, str) and role.lower() == DOCTOR_ROLE_VALUE

def _doctor_profile_exists(user) -> bool:
    return Doctor.objects.filter(user_id=user.id).exists()


def auto_login_view(request):
    token = request.GET.get('token')
    next_url = request.GET.get('next')  # optional

    if not token:
        return HttpResponseBadRequest("Missing token.")

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        if payload.get('type') != 'auto-login':
            return HttpResponseBadRequest("Invalid token type.")
        user_id = payload.get('user_id')
        if not user_id:
            return HttpResponseBadRequest("Invalid token payload.")
        user = User.objects.get(id=user_id)
        user.backend = 'accounts.backends.TenantAuthenticationBackend'
        login(request, user)

        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)    
        if _is_doctor(user) and not _doctor_profile_exists(user):
            return redirect('/finance/enroll_doctor')
        return redirect('/')

    except jwt.ExpiredSignatureError:
        return HttpResponseBadRequest("Token expired.")
    except jwt.InvalidTokenError:
        return HttpResponseBadRequest("Invalid token.")
    except User.DoesNotExist:
        return HttpResponseBadRequest("User not found.")

##################################################################


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        exclude = ['created_at']



@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def doctor_profile_view(request):
    user = request.user
    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        doctor = None

    if request.method == 'GET':
        if doctor:
            serializer = DoctorSerializer(doctor)
            return Response(serializer.data)
        return Response({'detail': 'No profile found.'}, status=404)

    if request.method in ['POST', 'PUT']:
        serializer = DoctorSerializer(instance=doctor, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save(user=user)
            return Response(DoctorSerializer(instance).data)
        return Response(serializer.errors, status=400)


class DoctorProfileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            doctor = Doctor.objects.get(user=request.user)
            serializer = DoctorSerializer(doctor)
            return Response(serializer.data)
        except Doctor.DoesNotExist:
            return Response({"detail": "Doctor profile not found."}, status=404)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'email': user.email,
    })







###################################################################
# mobile_api/views.py
from rest_framework import generics, permissions, status, serializers
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from chat.models import ChatThread, ChatMessage
from .serializers import ChatThreadSerializer, ChatMessageSerializer


class ChatThreadListView(generics.ListAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatThread.objects.filter(
            Q(doctor_user=user) | Q(patient_user=user),
            is_active=True
        ).order_by('-last_message_at', '-created_at')


class ChatMessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        thread_id = self.kwargs.get("thread_id")

        thread = ChatThread.objects.filter(
            id=thread_id,
            is_active=True
        ).filter(
            Q(doctor_user=user) | Q(patient_user=user)
        ).first()

        if not thread:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You are not allowed to view this thread")

        return ChatMessage.objects.filter(thread=thread).order_by('sent_at')



from rest_framework import generics, permissions, status, serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db.models import Q
from chat.models import ChatThread, ChatMessage
from .serializers import ChatMessageSerializer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class SendMessageAPIView(generics.CreateAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # text + file upload

    def perform_create(self, serializer):
        user = self.request.user
        thread_id = self.request.data.get("thread_id")
        text = self.request.data.get("text", "").strip()
        media_file = self.request.data.get("media", None)

        if not thread_id:
            raise serializers.ValidationError({"thread_id": "This field is required."})
        if not text and not media_file:
            raise serializers.ValidationError({"error": "Empty message."})

        # Check thread exists and user is participant
        thread = ChatThread.objects.filter(
            id=thread_id,
            is_active=True
        ).filter(
            Q(doctor_user=user) | Q(patient_user=user)
        ).first()

        if not thread:
            raise permissions.PermissionDenied("You cannot send messages to this thread.")

        # Save message
        msg = serializer.save(thread=thread, sender=user, text=text, media=media_file)

        # Update thread timestamp
        thread.last_message_at = msg.sent_at
        thread.save(update_fields=["last_message_at"])

        # Push to channels
        sender_id = user.id
        recipient_id = thread.patient_user_id if thread.doctor_user_id == sender_id else thread.doctor_user_id
        tenant_schema = getattr(getattr(self.request, "tenant", None), "schema_name", "public")
        tenant_prefix = tenant_schema
        group_sender = f"{tenant_prefix}_user_{sender_id}"
        group_recipient = f"{tenant_prefix}_user_{recipient_id}"
        channel_layer = get_channel_layer()

        payload = {
            "type": "chat_message",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "sender_name": user.get_full_name() or user.username,
            "message": msg.text or "",
            "media_url": msg.media.url if msg.media else None,
            "thread_id": thread.id,
            "sent_at": msg.sent_at.isoformat(),
        }

        async_to_sync(channel_layer.group_send)(group_sender, payload)
        async_to_sync(channel_layer.group_send)(group_recipient, payload)

        # Optional notification
        notification_payload = {
            "type": "chat_notify",
            "sender_id": sender_id,
            "sender_name": user.get_full_name() or user.username,
            "preview": msg.text[:80] if msg.text else "📎 Media file",
            "thread_id": thread.id,
            "sent_at": msg.sent_at.isoformat(),
            "notification": "New message received",
        }
        if recipient_id != sender_id:
            async_to_sync(channel_layer.group_send)(group_recipient, notification_payload)

        return msg

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        msg = self.perform_create(serializer)
        return Response({
            "id": msg.id,
            "sender": msg.sender.get_full_name() or msg.sender.username,
            "sender_id": msg.sender.id,
            "text": msg.text or "",
            "media_url": msg.media.url if msg.media else None,
            "sent_at": msg.sent_at.strftime("%Y-%m-%d %H:%M"),
        }, status=status.HTTP_201_CREATED)
