from django.contrib import admin

from.models import DoctorPayment,AIPrescriptionPayment,DoctorServiceLog,PaymentProfile,DoctorPaymentLog

admin.site.register(DoctorPayment)
admin.site.register(AIPrescriptionPayment)
admin.site.register(DoctorServiceLog)
admin.site.register(PaymentProfile)
admin.site.register(DoctorPaymentLog)
