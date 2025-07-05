from django.contrib import admin
from.models import PaymentSystem,TenantPaymentConfig,PaymentInvoice,Payment

admin.site.register(PaymentSystem)
admin.site.register(TenantPaymentConfig)
admin.site.register(PaymentInvoice)
admin.site.register(Payment)
