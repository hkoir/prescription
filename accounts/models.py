from django.contrib.auth.models import User
from django.db import models
from django.contrib.auth.models import AbstractUser
from clients.models import Client




class CustomUser(AbstractUser):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='tenant_users', null=True, blank=True)   
    biometrict_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('parent', 'Parent'),
        ('doctor', 'Doctor'),
        ('consultant', 'Consultant'),
        ('patient', 'Patient'),
        ('staff', 'Staff'),
        ('superadmin', 'SuperAdmin'),
    ]

    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='patient')
   
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)   
    photo_id = models.ImageField(upload_to='user_photo', null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.username} - {self.role}"
