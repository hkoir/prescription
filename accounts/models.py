from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import AbstractUser
from clients.models import Client

import random
from django.utils import timezone
from datetime import timedelta



class CustomUser(AbstractUser):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='tenant_users', null=True, blank=True)   
    biometrict_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    ROLE_CHOICES = [
        
        ('doctor', 'Doctor'),      
        ('patient', 'Patient'),
        ('staff', 'Staff'),
      
    ]
    

    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient')
    email = models.EmailField(blank=True, null=True, unique=False)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)   
    photo_id = models.ImageField(upload_to='user_photo', null=True, blank=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']  # keep username if still used internally

    def __str__(self):
        return f"{self.username}-{self.email}-{self.phone_number}"





class PhoneOTP(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    otp = models.CharField(max_length=6)
    valid_until = models.DateTimeField() 
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):     
        if not self.valid_until:
            self.valid_until = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

 
    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.valid_until = timezone.now() + timedelta(minutes=5)
        self.save()



from django.utils.translation import gettext_lazy as _
import uuid
class Address(models.Model):  
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(CustomUser, verbose_name=_("Customer"), on_delete=models.CASCADE)
    full_name = models.CharField(_("Full Name"), max_length=150)
    phone = models.CharField(_("Phone Number"), max_length=50)
    postcode = models.CharField(_("Postcode"), max_length=50)
    address_line = models.CharField(_("Address Line 1"), max_length=255)
    address_line2 = models.CharField(_("Address Line 2"), max_length=250,blank=True, null=True)
    town_city = models.CharField(_("Town/City/State"), max_length=150)
    delivery_instructions = models.CharField(_("Delivery Instructions"), max_length=255)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)
    default = models.BooleanField(_("Default"), default=False)  

   
    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return "Address"