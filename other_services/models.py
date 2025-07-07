from django.db import models


class NearbyService(models.Model):
    SERVICE_CHOICES = [
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('pharmacy', 'Pharmacy'),
        ('lab', 'Lab'),
    ]

    name = models.CharField(max_length=255)
    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"
