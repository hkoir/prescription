
from datetime import datetime, time, timedelta
from .forms import DoctorForm
from django.shortcuts import render, get_object_or_404,redirect
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from collections import defaultdict
from django.utils.timezone import make_aware
from django.db.models import Count
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.core.paginator import Paginator

from prescription.models import Doctor,Specialization
from .models import AppointmentSlot,Appointment
from prescription.models import Patient
from .forms import TimeSlotForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from.models import AppointmentSlot
from datetime import datetime, timedelta



def generate_time_slots(doctor, slot_duration, start_date, end_date):
    # Validate dates
    if not start_date or not end_date or start_date > end_date:
        return False

    # Validate doctor's available hours
    if not doctor.start_time or not doctor.end_time:
        return False  # Or raise a specific error message if needed

    slot_delta = timedelta(minutes=slot_duration)

    for single_date in (start_date + timedelta(days=n) for n in range((end_date - start_date).days + 1)):
        current_time = doctor.start_time

        while current_time < doctor.end_time:
            slot_end_time = (datetime.combine(single_date, current_time) + slot_delta).time()
            AppointmentSlot.objects.create(
                doctor=doctor,
                date=single_date,
                start_time=current_time,
                end_time=slot_end_time,
                slot_duration=slot_duration,
                is_booked=False
            )
            current_time = slot_end_time  # Move to next slot

    return True



 
def generate_monthly_timeslots(doctor_id, year, month, start_time="09:00", end_time="17:00", slot_duration=30):
  
    doctor = Doctor.objects.get(id=doctor_id)
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month + 1, 1) - timedelta(days=1)  # Last day of the month

    current_date = first_day
    slots_created = 0

    while current_date <= last_day:       
        if current_date.weekday() not in [5, 6]:           
            aware_date = make_aware(datetime.combine(current_date, datetime.min.time()))           
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")

            current_time = start_dt
            while current_time < end_dt:
                slot_start = make_aware(datetime.combine(current_date, current_time.time()))
                slot_end = make_aware(datetime.combine(current_date, (current_time + timedelta(minutes=slot_duration)).time()))

                # Create timeslot entry
                AppointmentSlot.objects.create(
                    doctor=doctor,
                    date=aware_date.date(),
                    start_time=slot_start.time(),
                    end_time=slot_end.time(),
                    is_booked=False
                )

                slots_created += 1
                current_time += timedelta(minutes=slot_duration)  # Move to next slot
        current_date += timedelta(days=1)  # Move to next day
    print(f"{slots_created} timeslots generated for Doctor {doctor_id} (excluding weekends).")



@login_required
def create_doctor_timeslots(request, id=None):  
    instance = get_object_or_404(AppointmentSlot, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = TimeSlotForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST':
        if form.is_valid():
            form_instance = form.save(commit=False)
            doctor = form.cleaned_data.get("doctor")
            slot_duration = form.cleaned_data.get("slot_duration")
            start_date = form.cleaned_data.get("start_date")
            end_date = form.cleaned_data.get("end_date")

            # ✅ Check if both dates are present
            if start_date and end_date:
                success = generate_time_slots(doctor, slot_duration, start_date, end_date)
                if success:
                    messages.success(request, f"Time slots {message_text}")
                    return redirect("appointments:create_doctor_timeslots")
                else:
                    messages.success(request, f"Fail to create time slots, Please check all the form fields")
                    form.add_error(None, "End date must be after start date.")
            else:
                form.add_error(None, "Start date and End date are required.")
        # form is invalid or error above — fall through to re-render form with errors

    datas = AppointmentSlot.objects.all().order_by('-date')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'appointments/manage_doctor_timeslots.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })


@login_required
def delete_doctor_timeslots(request, id):
    instance = get_object_or_404(AppointmentSlot, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('appointments:create_doctor_timeslots')  

    messages.warning(request, "Invalid delete request!")
    return redirect('appointments:create_doctor_timeslots')  



from clients.utils import tenant_only_view
@login_required
def available_doctors(request):
    appointments = Appointment.objects.select_related("patient", "timeslot").all()
    query = request.GET.get("query", "").strip()
    specialization_filter = request.GET.get("specialization", "").strip()
    doctors = Doctor.objects.all()
    if query:
        doctors = doctors.filter(full_name__icontains=query)
    
    if specialization_filter:
        doctors = doctors.filter(specialization__icontains=specialization_filter)  # ✅ Correct


    categorized_doctors = {}
    for doctor in doctors:
        if doctor.specialization not in categorized_doctors:
            categorized_doctors[doctor.specialization] = []
        categorized_doctors[doctor.specialization].append(doctor)

    return render(request, "appointments/available_doctors.html", {
        "categorized_doctors": categorized_doctors,
        "query": query,
        "specialization_filter": specialization_filter,
        'appointments': appointments
    })




def doctor_list(request):
    query = request.GET.get('q', '')
    doctors = Doctor.objects.all()

    if query:
        doctors = doctors.filter(
            Q(name__icontains=query) | 
            Q(specialization__name__icontains=query)
        )

    doctors = doctors.order_by('name')
    return render(request, 'appointments/doctor_list.html', {'doctors': doctors, 'query': query})



def view_available_slots2(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    date = request.GET.get('date')

    slots = []
    if date:
        # Filter or generate slots for that doctor on that date
        slots = AppointmentSlot.objects.filter(doctor=doctor, date=date)

    return render(request, 'appointments/available_slots.html', {
        'doctor': doctor,
        'slots': slots,
        'selected_date': date,
    })



def view_available_slots(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    date = request.GET.get('date')

    appointment_type = request.GET.get('type')  # "followup" or None
    parent_appointment_id = request.GET.get('parent')  # e.g., "42"

    slots = []
    if date:
        slots = AppointmentSlot.objects.filter(doctor=doctor, date=date)

    return render(request, 'appointments/available_slots.html', {
        'doctor': doctor,
        'slots': slots,
        'selected_date': date,
        'appointment_type': appointment_type,
        'parent_appointment_id': parent_appointment_id,
    })




def get_timeslots(request):
    doctor_id = request.GET.get("doctor_id")
    date = request.GET.get("date")
    slots = AppointmentSlot.objects.filter(doctor_id=doctor_id, date=date,is_booked =False)
    doctor = get_object_or_404(Doctor, id =doctor_id)
    consultation_fees = doctor.consultation_fees
    

    slots_list = [
        {
            "id": slot.id,  
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "is_booked": slot.is_booked,  # Include booking status
            "consultation_fee": consultation_fees
        }
        for slot in slots
    ]

    return JsonResponse({"slots": slots_list})




@csrf_exempt
@login_required
def book_slot2(request):
    if request.method == "POST":
        with transaction.atomic():
            try:
                slot_id = request.POST.get("slot_id")
                doctor_id = request.POST.get("doctor_id")
                name = request.POST.get("name")
                phone = request.POST.get("phone")
                dob_str = request.POST.get("date_of_birth")
                date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
                email = request.POST.get("email")
                gender = request.POST.get("gender")
                address = request.POST.get("address")
                medical_history = request.POST.get("medical_history")
                photo = request.FILES.get("patient_photo")

                # Get or create patient
                try:
                    patient = Patient.objects.get(user=request.user)
                    message = f"Welcome back, {patient.full_name}! Your profile has been reused."
                except Patient.DoesNotExist:
                    patient = Patient.objects.create(
                        user=request.user,
                        full_name=name,
                        phone=phone,
                        dob=date_of_birth,
                        email=email,
                        gender=gender,
                        address=address,
                        medical_history=medical_history,
                      
                    )
                    message = f"Thank you {patient.full_name}, your profile has been created."

                # Booking logic
                slot = AppointmentSlot.objects.get(id=slot_id, is_booked=False)
                doctor = Doctor.objects.get(id=doctor_id)

                appointment = Appointment.objects.create(
                    timeslot=slot,
                    patient=patient,
                    doctor=doctor,
                    user=request.user,
                    patient_type="OPD"
                )

                slot.is_booked = True
                slot.save()

                return JsonResponse({
                    "success": True,
                    "message": f"{message} Appointment with Dr. {doctor.full_name} on {slot.date} from {slot.start_time} to {slot.end_time} has been confirmed."
                })

            except AppointmentSlot.DoesNotExist:
                return JsonResponse({"success": False, "error": "Slot does not exist or is already booked."})
            except Doctor.DoesNotExist:
                return JsonResponse({"success": False, "error": "Doctor does not exist."})
            except Exception as e:
                print(f"Error: {str(e)}")
                return JsonResponse({"success": False, "error": "An unexpected error occurred."})

    return JsonResponse({"success": False, "error": "Invalid request method."})

import traceback
import logging
logger = logging.getLogger(__name__) 


@csrf_exempt
@login_required
def book_slot(request):
    if request.method == "POST":
        with transaction.atomic():
            try:
                slot_id = request.POST.get("slot_id")
                doctor_id = request.POST.get("doctor_id")
                parent_id = request.POST.get("parent_appointment_id")

                # Normalize parent_id to None if empty or 'None' string
                if parent_id in [None, '', 'None']:
                    parent_id = None

                name = request.POST.get("name")
                phone = request.POST.get("phone")
                dob_str = request.POST.get("date_of_birth")
                date_of_birth = datetime.strptime(dob_str, "%Y-%m-%d").date() if dob_str else None
                email = request.POST.get("email")
                gender = request.POST.get("gender")
                address = request.POST.get("address")
                medical_history = request.POST.get("medical_history")
                photo = request.FILES.get("patient_photo")

                # Get or create patient
                try:
                    patient = Patient.objects.get(user=request.user)
                    message = f"Welcome back, {patient.full_name}! Your profile has been reused."
                except Patient.DoesNotExist:
                    patient = Patient.objects.create(
                        user=request.user,
                        full_name=name,
                        phone=phone,
                        dob=date_of_birth,
                        email=email,
                        gender=gender,
                        address=address,
                        medical_history=medical_history,
                        # photo=photo  # add if model has it
                    )
                    message = f"Thank you {patient.full_name}, your profile has been created."

                slot = AppointmentSlot.objects.get(id=slot_id, is_booked=False)
                doctor = Doctor.objects.get(id=doctor_id)

                parent_appointment = None
                if parent_id is not None:
                    try:
                        parent_appointment = Appointment.objects.get(id=int(parent_id))
                    except (Appointment.DoesNotExist, ValueError) as e:
                        logger.warning(f"Invalid parent appointment id {parent_id}: {e}")
                        parent_appointment = None

                appointment = Appointment.objects.create(
                    timeslot=slot,
                    patient=patient,
                    doctor=doctor,
                    user=request.user,
                    patient_type="OPD",
                    parent=parent_appointment,
                    appointment_type="followup" if parent_appointment else "initial"
                )

                slot.is_booked = True
                slot.save()

                return JsonResponse({
                    "success": True,
                    "message": f"{message} Appointment with Dr. {doctor.full_name} on {slot.date} from {slot.start_time} to {slot.end_time} has been confirmed."
                })

            except AppointmentSlot.DoesNotExist:
                return JsonResponse({"success": False, "error": "Slot does not exist or is already booked."})
            except Doctor.DoesNotExist:
                return JsonResponse({"success": False, "error": "Doctor does not exist."})
            except Exception as e:
                logger.error("Unexpected error in book_slot: %s", e, exc_info=True)
                return JsonResponse({"success": False, "error": "An unexpected error occurred."})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@login_required
def general_appointment(request):
    doctors = Doctor.objects.all()
    patients = Patient.objects.all()

    if request.method == "POST":
        doctor_id = request.POST.get("doctor_id")
        slot_id = request.POST.get("slot_id")
        patient_id = request.POST.get("patient_id")
        appointment_date = request.POST.get("appointment_date")
        consultation_fee = request.POST.get("consultation_fee")
        patient_type_choice = request.POST.get("patient_type")

        # Validate patient type
        if patient_type_choice not in ['OPD', 'IPD', 'Emergency']:
            messages.error(request, 'Invalid patient type selected.')
            return redirect('appointments:general_appointment')

        if not all([doctor_id, slot_id, appointment_date, consultation_fee, patient_id]):
            messages.error(request, "All fields are required.")
            return redirect('appointments:general_appointment')

        # Validate objects
        slot = get_object_or_404(AppointmentSlot, id=slot_id, is_booked=False)
        doctor = get_object_or_404(Doctor, id=doctor_id)
        patient = get_object_or_404(Patient, id=patient_id)

        # Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            timeslot=slot,
            date=appointment_date,
            patient_type=patient_type_choice,
            user=request.user,
            payment_status='UnPaid',
        )

        # Mark slot as booked
        slot.is_booked = True
        slot.save()         
      
        messages.success(request, "Appointment booked successfully.")
        return redirect("appointments:appointment_list")

    return render(request, "appointments/general_appointment_booking.html", {
        "doctors": doctors,
        "patients": patients,
    })



# This view is not for this application
def specialization_detail(request, specialization_id):
    appointments = Appointment.objects.select_related("patient", "timeslot").all()
    specialization = get_object_or_404(Specialization, id=specialization_id)   
    specializations = Specialization.objects.all()


    query = request.GET.get("query", "").strip() 
    doctors = specialization.specialized_doctors.all()  

    if query:
        doctors = doctors.filter(name__icontains=query)  

    return render(request, "appointments/specialization_details.html", {
        "specialization": specialization,
        "doctors": doctors,
        "query": query, 
        'appointments':  appointments,
        'specializations':specializations
        
    })



def get_doctors_by_specialization(request):
    specialization = request.GET.get("specialization", None)

    if specialization and specialization != "all":
        doctors = Doctor.objects.filter(specialization=specialization)
    else:
        doctors = Doctor.objects.all()

    doctor_data = [
        {
            "id": doctor.id,
            "name": doctor.name,
            "specialization": doctor.specialization,
            "experience_years": doctor.experience_years,
            "employee_photo_ID": doctor.employee_photo_ID.url if doctor.employee_photo_ID else "",
        }
        for doctor in doctors
    ]
    return JsonResponse({"doctors": doctor_data})





from django.db.models import Count, Prefetch
from django.utils import timezone

def appointment_list(request):
    today = timezone.now().date()

    # Base queryset depending on role
    if request.user.role == 'doctor':
        doctor_qs = Doctor.objects.filter(user=request.user)
        if doctor_qs.exists():
            appointments = Appointment.objects.filter(doctor__in=doctor_qs)
        else:
            appointments = Appointment.objects.none()

    elif request.user.role == 'patient':
        patient_qs = Patient.objects.filter(user=request.user)
        if patient_qs.exists():
            appointments = Appointment.objects.filter(patient__in=patient_qs)
        else:
            appointments = Appointment.objects.none()
            
    else:
        appointments = Appointment.objects.all()  # staff/admin sees all

    # Apply filters from query parameters
    doctor_filter = request.GET.get("doctor")
    patient_filter = request.GET.get("patient")
    date_filter = request.GET.get("date", "").strip()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if doctor_filter:
        appointments = appointments.filter(doctor__id=doctor_filter)

    if patient_filter:
        appointments = appointments.filter(patient__id=patient_filter)

    if date_filter:
        appointments = appointments.filter(date=date_filter)

    if start_date and end_date:
        appointments = appointments.filter(date__range=[start_date, end_date])

    # Default to today's appointments only if no filters
    if not (doctor_filter or patient_filter or date_filter or (start_date and end_date)):
        appointments = appointments.filter(date=today)

    # For summary or grouping
    doctor_appointment_counts = (
        appointments.values("doctor__id", "doctor__full_name")
        .annotate(total_appointments=Count("id"))
        .order_by("-total_appointments")
    )

    # Initial appointments with related follow-ups (apply same filters)
    initial_appointments = appointments.filter(appointment_type='initial').prefetch_related(
        Prefetch('followups', queryset=appointments)
    ).order_by('-date', 'timeslot__start_time')

    doctors = Doctor.objects.all()
    patients = Patient.objects.all()

    return render(request, "appointments/appointment_list.html", {
        "appointments": appointments,
        "doctor_appointment_counts": doctor_appointment_counts,
        "today": today,
        "doctors": doctors,
        "patients": patients,
        "initial_appointments": initial_appointments,
    })


@login_required
def appointment_detail(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if request.user.role == 'doctor' and appointment.doctor.user != request.user:
        return render(request, "403.html")  
    if appointment.appointment_type == 'followup' and appointment.parent:
        initial_appointment = appointment.parent
    else:
        initial_appointment = appointment   
    followups = initial_appointment.followups.all().order_by('date', 'timeslot__start_time')

    return render(request, "appointments/appointment_detail.html", {
        "initial_appointment": initial_appointment,
        "selected_appointment": appointment,  # The one user clicked on
        "followups": followups,
    })


@csrf_exempt
def cancel_appointment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            appointment_id = data.get("appointment_id")

            if not appointment_id:
                return JsonResponse({"success": False, "error": "Appointment ID is required."})

            appointment = Appointment.objects.get(id=appointment_id)
            slot = appointment.timeslot 

            appointment.status = 'Cancelled'
            appointment.save()
            slot.is_booked = False
            slot.save()
            
            return JsonResponse({"success": True, "message": "Appointment cancelled successfully!"})
        except Appointment.DoesNotExist:
            return JsonResponse({"success": False, "error": "Appointment does not exist."})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})





from payment_gateway.models import PaymentInvoice


@login_required
def booking_confirmation_payment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.status == 'Cancelled':
        messages.warning(request, 'Cannot process payment: Appointment is cancelled.')
        return redirect('appointments:appointment_list')

    if appointment.payment_status == 'Paid':
        messages.info(request, 'This appointment has already been paid.')
        return redirect('appointments:appointment_list')

    patient = appointment.patient
    doctor = appointment.doctor

    last_visit = (
        Appointment.objects.filter(patient=patient, doctor=doctor, status='Prescription-Given')
        .exclude(id=appointment.id)
        .order_by('-date')
        .first()
    )
 
    doctor_fee = doctor.consultation_fees
    if last_visit and doctor.followup_validity_days:
        days_since_last = (appointment.date - last_visit.date).days
        if days_since_last <= doctor.followup_validity_days:
            doctor_fee = doctor.folloup_consultation_fees

    if request.method == 'POST':
        invoice = PaymentInvoice.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            invoice_type='appointment',
            amount=doctor_fee,
            is_paid=True
        )
        appointment.payment_status = 'Paid'
        appointment.save()

        return redirect('appointments:invoice_detail', invoice_id=invoice.id)

    context = {
        'appointment': appointment,
        'patient': patient,
        'doctor_fee': doctor_fee,
    }
    return render(request, 'appointments/booking_confirmation_payment.html', context)


from prescription.models import DoctorPrescription,SuggestedLabTest,SuggestedMedicine,LabTest
from prescription.forms import DoctorPrescriptionForm,SuggestedLabTestForm,SuggestedMedicineForm
import re
from django.forms import modelformset_factory

PrescriptionFormSet = modelformset_factory(
    SuggestedMedicine,
    form=SuggestedMedicineForm,
    extra=1,
    can_delete=True,
)  


@login_required
def create_prescription_from_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    doctor = appointment.doctor
    patient = appointment.patient

    if doctor.user != request.user:
        messages.error(request, "You are not authorized to create a prescription for this appointment.")
        return redirect('appointments:appointment_list')

    existing_prescription = DoctorPrescription.objects.filter(appointment_ref=appointment).first()
    last_prescription = DoctorPrescription.objects.filter(appointment_ref=appointment).last()
    previous_lab_tests = []
    if last_prescription:
        previous_lab_tests = SuggestedLabTest.objects.filter(prescription=last_prescription)

    if request.method == 'POST':
        medical_form = DoctorPrescriptionForm(request.POST, request.FILES, instance=existing_prescription)
        prescription_formset = PrescriptionFormSet(request.POST, queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm(request.POST) 

        if medical_form.is_valid() and prescription_formset.is_valid() and lab_test_form.is_valid():
            with transaction.atomic():
                doctor_prescription = medical_form.save(commit=False)
                doctor_prescription.patient = patient
                doctor_prescription.doctor = doctor
                doctor_prescription.appointment_ref = appointment
                doctor_prescription.save()

                for form in prescription_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        prescribed_medicine = form.save(commit=False)
                        prescribed_medicine.prescription = doctor_prescription
                        prescribed_medicine.save()

                selected_lab_tests = request.POST.getlist('lab_tests')
                for test_id in selected_lab_tests:
                    lab_test_catalog = LabTest.objects.filter(id=test_id).first()
                    if lab_test_catalog:
                        SuggestedLabTest.objects.create(
                            prescription=doctor_prescription,
                            lab_test_name=lab_test_catalog,
                            lab_test_notes='Pending'
                        )

                # Custom lab tests
                custom_tests_raw = request.POST.get('custom_lab_tests', '')
                custom_tests = re.split(r'[\n,]+|\s{2,}', custom_tests_raw)
                custom_tests = [test.strip() for test in custom_tests if test.strip()]
                for test_name in custom_tests:
                    SuggestedLabTest.objects.create(
                        prescription=doctor_prescription,
                        custom_lab_test_name=test_name
                    )

                # Mark appointment as completed (optional)
                appointment.status = 'Prescription-Given'
                appointment.save()

                messages.success(request, "Prescription created successfully.")
                return redirect('prescription:doctor_prescription_list')

    else:
        medical_form = DoctorPrescriptionForm(instance=existing_prescription)
        prescription_formset = PrescriptionFormSet(queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm()

    return render(request, 'prescription/create_doctor_prescription.html', {
        'booking': appointment,  # for template compatibility
        'medical_form': medical_form,
        'prescription_formset': prescription_formset,
        'lab_test_form': lab_test_form,
        'lab_tests': LabTest.objects.all(),
        "last_prescription": last_prescription,
        "previous_lab_tests": previous_lab_tests,
    })



@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(PaymentInvoice, id=invoice_id)
    return render(request, 'appointments/invoice_detail.html', {'invoice': invoice})
