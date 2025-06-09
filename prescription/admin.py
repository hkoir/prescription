from django.contrib import admin
from.models import AIPrescription,Patient,Doctor,SuggestedLabTest,SuggestedMedicine,DoctorPrescription
from.models import LabTest,Medicine,DoctorBooking,DoctorFolloupBooking,ZoomMeeting

admin.site.register(AIPrescription)
admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(DoctorPrescription)
admin.site.register(SuggestedLabTest)
admin.site.register(SuggestedMedicine)

admin.site.register(LabTest)
admin.site.register(Medicine)
admin.site.register(DoctorBooking)

admin.site.register(DoctorFolloupBooking)
admin.site.register(ZoomMeeting)

