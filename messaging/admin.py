from django.contrib import admin

from.models import Notification,Message,ManagementMessage

admin.site.register(Notification)
admin.site.register(Message)
admin.site.register(ManagementMessage)
