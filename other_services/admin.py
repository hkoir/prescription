
from django.contrib import admin
from .models import NearbyService

@admin.register(NearbyService)
class NearbyServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'service_type', 'address']
    search_fields = ['name', 'service_type']
