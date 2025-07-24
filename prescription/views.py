from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
import json
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
import base64
from django.core.files.base import ContentFile
from django.core.exceptions import PermissionDenied
from django.urls import reverse
import re
from django.utils.translation import get_language
from django.core.paginator import Paginator

from .models import DoctorBooking, DoctorPrescription, SuggestedMedicine, SuggestedLabTest,LabTest
from .models import AIPrescription,Patient,DoctorBooking,Doctor
from .forms import DoctorPrescriptionForm, SuggestedMedicineForm, SuggestedLabTestForm,AIPrescriptionForm,PatientForm,DirectDoctorBookingForm
from finance.models import DoctorPayment,DoctorServiceLog,PaymentProfile,AIPrescriptionPayment
from finance.utils import update_doctor_payment
from .forms import MedicineForm, LabTestForm
from.models import Medicine,LabTest
from.forms import RequestVideoCallForm,ApproveRequestVideoCallForm
from.forms import PatientZoomRequestForm,DoctorZoomScheduleForm
from.models import ZoomMeeting
from.forms import DoctorFolloupBookingApprovedForm,DoctorFolloupBookingRequestForm
from.models import DoctorFolloupBooking
from prescription.utils.zoom import create_zoom_meeting
from payment_gateway.utils import is_payment_enabled_for_tenant

from.models import LabResultFile

from django.core.mail import send_mail
from django.conf import settings
from django.core.files.storage import default_storage
from tempfile import NamedTemporaryFile
import mimetypes
from.models import AiLabImageInterpretation
from .ai import get_ai_prescription  
from prescription.ai import get_ai_prescription_with_image  
from .ai import interpret_lab_images_only  
import re
import requests


def about_us(request):
    return render(request, 'prescription/about_us.html')


from django.core.mail import send_mail
from django.conf import settings

def contact_us(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        full_message = f"Message from {name} ({email}):\n\n{message}"
   
        send_mail(
            subject=subject,
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],  # set this in settings.py
            fail_silently=False
        )

        messages.success(request, "Your message has been sent successfully. We'll get back to you soon.")
        return redirect('prescription:contact_us')
    return render(request, 'prescription/contact_us.html')




def home(request):
    return render(request,'prescription/home.html')




@login_required
def available_doctors(request):
    prescription_id = request.GET.get("prescription_id")
    ai_prescription = get_object_or_404( AIPrescription, id=prescription_id) if prescription_id else None

    
    query = request.GET.get("query", "").strip()
    specialization_filter = request.GET.get("specialization", "").strip()
    doctors = Doctor.objects.all()
    if query:
        doctors = doctors.filter(full_name__icontains=query)
    
    if specialization_filter:
        doctors = doctors.filter( specialization__icontains=specialization_filter)  # ✅ Correct


    categorized_doctors = {}
    for doctor in doctors:
        if doctor.specialization not in categorized_doctors:
            categorized_doctors[doctor.specialization] = []
        categorized_doctors[doctor.specialization].append(doctor)

    return render(request, "prescription/available_doctors.html", {
        "categorized_doctors": categorized_doctors,
        "query": query,
        "specialization_filter": specialization_filter,
        'ai_prescription': ai_prescription
       
    })



PaymentGatewayAPI=None

def process_payment(payment_token, amount, currency='usd'):
    payment_gateway = PaymentGatewayAPI(api_key="your_api_key")    
    try:
        charge_response = payment_gateway.charge_card(
            token=payment_token,
            amount=amount,
            currency=currency
        )
        
        if charge_response['status'] == 'success':
            return True
        else:
            return False
    except Exception as e:
        return False






def extract_section(text, pattern, fallback=""):
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else fallback




from payment_gateway.utils import create_payment_invoice
from payment_gateway.models import Payment
from payment_gateway.models import Payment, PaymentInvoice
from accounts.utils import send_sms
from messaging.views import create_notification
import re



@login_required
def initiate_ai_prescription_payment(request):
    patient =None
  
    try:
        patient = request.user.patient_profile
        patient.refresh_from_db()  # Always refresh to get updated usage
    except Patient.DoesNotExist:
        messages.error(request, "You need a patient profile to continue.")
        return redirect(f"{reverse('prescription:create_patient_profile')}?next={request.path}")
   
    free_limit = getattr(patient, 'free_ai_prescription_limit',5)  # default to 5 if not set
    used = patient.free_ai_prescriptions_used

    print(f"Free limit = {free_limit}, Used = {used}")

    if used < free_limit:
        messages.info(request, f"You are within the free AI prescription limit ({used}/{free_limit}).")
        return redirect('prescription:create_ai_prescription')

    # Check if they already paid but haven't used it yet
    existing_payment = AIPrescriptionPayment.objects.filter(
        patient=patient,
        used_for_prescription=False,
        successful=True
    ).first()

    if existing_payment:
        messages.info(request, "You already have a paid AI prescription available.")
        return redirect('prescription:create_ai_prescription')

    messages.warning(request, 'You’ve exceeded the free AI usage limit. Please complete the payment process.')
    amount = 100.0
    invoice = create_payment_invoice(
        patient=patient,
        invoice_type='ai_prescription',
        amount=amount,
        description="AI Prescription Fee",
        related_object_id=0,
        ai_prescription=None
    )
    request.session['ai_prescription_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')


#===============================================================================================




@login_required
def create_ai_prescription(request):
    form = AIPrescriptionForm()
    patient_form = PatientForm()
    user = request.user  
    patient = None
    patient_missing = False
    free_limit = 5
    free = False
    payment = None

    try:
        patient = user.patient_profile
    except Patient.DoesNotExist:
        patient_missing = True
    if patient and patient.needs_profile_update():
        return redirect(f"{reverse('finance:update_patient_profile', args=[patient.id])}?next={request.path}")


    # Prevent GET form rendering if patient exceeded free usage and no payment
    if request.method != 'POST' and patient and patient.free_ai_prescriptions_used >= free_limit:
        has_payment = AIPrescriptionPayment.objects.filter(
            patient=patient,
            used_for_prescription=False,
            successful=True
        ).exists()
        if not has_payment:
            messages.warning(request, 'Your free AI prescription limit has been reached. Please make a payment to continue.')
            return redirect('prescription:home')     
    
    if request.method == 'POST':
        if 'create_patient' in request.POST:
            patient_form = PatientForm(request.POST)
            if patient_form.is_valid():
                patient_instance = patient_form.save(commit=False)
                patient_instance.user = user
                patient_instance.save()
                messages.success(request, "Patient profile created.")
                return redirect('prescription:create_ai_prescription')
        else:
            form = AIPrescriptionForm(request.POST)
            if not patient:
                messages.error(request, "Please complete your patient profile before proceeding.")
                return redirect('prescription:create_ai_prescription')

            if patient.free_ai_prescriptions_used < free_limit:
                free = True
            else:
                payment = AIPrescriptionPayment.objects.filter(
                    patient=patient,
                    used_for_prescription=False,
                    successful=True
                ).first()
                if not payment:
                    messages.warning(request, 'Your free usage has ended. Please make a payment to generate a new AI prescription.')
                    return redirect('payment:start_ai_payment')  # Redirect again here on failed POST
                                                               

            if form.is_valid():
                data = form.cleaned_data # covering symptoms,vital_signs,current_medications, duration            
                data['age'] = data.get('age') or patient.age
                data['gender'] = data.get('gender') or patient.gender
                data['body_weight'] = data.get('body_weight') or patient.body_weight              
                data['body_height'] = data.get('body_height') or patient.body_height
                data['location'] = data.get('location') or patient.city                
                data['medical_history'] = data.get('medical_history') or patient.medical_history
                data['allergies'] = data.get('allergies') or patient.allergies

                ai_data = get_ai_prescription(**data)
            #=================================================================================================
                invoice_id = request.session.get('ai_prescription_invoice_id')             
                invoice = None
                if invoice_id:
                    try:
                        invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='ai_prescription')
                    except PaymentInvoice.DoesNotExist:
                        messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                        return redirect('prescription:ai_prescription_list')
	#=====================================================================================================
                prescription = AIPrescription.objects.create(
                    user=user,
                    patient=patient,
                    symptoms=data['symptoms'],
                    duration=data['duration'],
                    age=data['age'],
                    gender=data['gender'],
                    medical_history=data.get('medical_history', ''),
                    allergies=data.get('allergies', ''),
                    current_medications=data.get('current_medications', ''),
                    vital_signs=data.get('vital_signs', ''),
                    location=data.get('location', ''),
                    summary_of_findings = ai_data['summary'],
                    diagnosis=ai_data['diagnosis'],
                    medicines=ai_data['medicines'],
                    tests=ai_data['tests'],
                    advice=ai_data['advice'],
                    recommended_specialty=ai_data['recommended_specialty'],
                    warning_signs=ai_data.get('warning_signs', ''),
		    diet_chart=ai_data.get('diet_chart'),
                    raw_response=ai_data["raw_content"] 
                )
	  #========================================================================
                if invoice:
                    invoice.ai_prescription = prescription
                    invoice.save()
                    del request.session['ai_prescription_invoice_id']
         #===========================================================================

                if free:
                    patient.free_ai_prescriptions_used += 1
                    patient.save()

                    AIPrescriptionPayment.objects.create(
                        patient=patient,
                        ai_prescription=prescription,
                        amount=0.0,
                        payment_status='free',
                        transaction_id='FREE',
                        used_for_prescription=True
                    )
                else:
                    payment.ai_prescription = prescription
                    payment.used_for_prescription = True
                    payment.save()

                return redirect('prescription:ai_prescription_detail', pk=prescription.pk)
    else:
        form = AIPrescriptionForm()
        patient_form = PatientForm()

    return render(request, 'prescription/create.html', {
        'form': form,
        'patient_form': patient_form,
        'patient_missing': patient_missing
    })



def normalize_duration_text(raw_duration):
    match = re.search(r'(\d+)', raw_duration)
    if not match:
        return raw_duration

    number = int(match.group(1))  # forces English numerals
    lang = get_language()

    if lang == 'bn':
        return f"{number} দিন"  # Bangla label, English number
    else:
        return f"{number} days"




def extract_recommended_specialty_from_raw(content):
    if not content:
        return "General"
    match = re.search(
        r"\*\*5\.\s*Recommended Specialist\s*:?\*\*\s*\n*(.*?)\s*(?=\*\*6\.|\Z)",
        content,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        specialty = match.group(1).strip() 
        specialty_cleaned = re.sub(r'\*+', '', specialty).strip()
        if specialty_cleaned and specialty_cleaned.lower() not in {"none", "n/a"}:
            return specialty_cleaned
    return "General"



@login_required
def create_ai_prescription_with_image(request):
    form = AIPrescriptionForm()
    patient_form = PatientForm()
    user = request.user
    patient = None
    patient_missing = False
    free = False
    payment = None

    try:
        patient = user.patient_profile
    except Exception:
        patient_missing = True

    if patient and patient.needs_profile_update():
        return redirect(f"{reverse('finance:update_patient_profile', args=[patient.id])}?next={request.path}")

    free_limit = getattr(patient, 'free_ai_prescription_limit', 5)
    if request.method != 'POST' and patient and patient.free_ai_prescriptions_used >= free_limit:
        has_payment = AIPrescriptionPayment.objects.filter(
            patient=patient,
            used_for_prescription=False,
            successful=True
        ).exists()
        if not has_payment:
            messages.warning(request, 'Your free AI prescription limit has been reached. Please make a payment to continue.')
            return redirect('prescription:home')

    if request.method == 'POST':
        if 'create_patient' in request.POST:
            patient_form = PatientForm(request.POST)
            if patient_form.is_valid():
                patient_instance = patient_form.save(commit=False)
                patient_instance.user = user
                patient_instance.save()
                messages.success(request, "Patient profile created.")
                return redirect('prescription:create_ai_prescription')
        else:
            form = AIPrescriptionForm(request.POST, request.FILES)
            if not patient:
                messages.error(request, "Please complete your patient profile before proceeding.")
                return redirect('prescription:create_ai_prescription')

            if patient.free_ai_prescriptions_used < free_limit:
                free = True
            else:
                payment = AIPrescriptionPayment.objects.filter(
                    patient=patient,
                    used_for_prescription=False,
                    successful=True
                ).first()
                if not payment:
                    messages.warning(request, 'Your free usage has ended. Please make a payment to generate a new AI prescription.')
                    return redirect('prescription:home')

            if form.is_valid():
                data = form.cleaned_data.copy()
                data.pop('lab_image', None)  # clean unused field

                # Fill missing values from patient profile
                data['age'] = data.get('age') or patient.age
                data['gender'] = data.get('gender') or patient.gender
                data['body_weight'] = data.get('body_weight') or patient.body_weight
                data['body_height'] = data.get('body_height') or patient.body_height
                data['location'] = data.get('location') or patient.city
                data['medical_history'] = data.get('medical_history') or patient.medical_history
                data['allergies'] = data.get('allergies') or patient.allergies

                uploaded_files = request.FILES.getlist('lab_files')

                # 🧠 Call AI ONCE with all images
                all_image_payloads = []
                for uploaded_file in uploaded_files:
                    with NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_file:
                        for chunk in uploaded_file.chunks():
                            tmp_file.write(chunk)
                        tmp_path = tmp_file.name

                    with open(tmp_path, "rb") as f:
                        image_bytes = f.read()

                    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
                    if not mime_type:
                        mime_type = "image/jpeg"

                    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

                    all_image_payloads.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded_image}",
                            "detail": "high"
                        }
                    })

                # Main AI Prescription (with all images as general context)
                ai_data = get_ai_prescription_with_image(
                    **data,
                    image_payloads=all_image_payloads
                )

                # Invoice check
                invoice = None
                invoice_id = request.session.get('ai_prescription_invoice_id')
                if invoice_id:
                    try:
                        invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='ai_prescription')
                    except PaymentInvoice.DoesNotExist:
                        messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                        return redirect('prescription:ai_prescription_list')

                # Save AIPrescription
               # ✅ Save prescription first (without lab images)
                prescription = AIPrescription.objects.create(
                    user=user,
                    patient=patient,
                    symptoms=data['symptoms'],
                    duration=data['duration'],
                    age=data['age'],
                    gender=data['gender'],
                    medical_history=data.get('medical_history', ''),
                    allergies=data.get('allergies', ''),
                    current_medications=data.get('current_medications', ''),
                    vital_signs=data.get('vital_signs', ''),
                    location=data.get('location', ''),
                    summary_of_findings="Pending",  # placeholder
                    diagnosis="Pending",  # placeholder
                    medicines="Pending",  # placeholder
                    tests="Pending",
                    advice="Pending",
                    recommended_specialty="",
                    warning_signs="",
                    diet_chart="",
                    raw_response=""
                )

                # ✅ For each file: call AI separately and save its interpretation
                for uploaded_file in uploaded_files:
                    with NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_file:
                        for chunk in uploaded_file.chunks():
                            tmp_file.write(chunk)
                        tmp_path = tmp_file.name

                    with open(tmp_path, "rb") as f:
                        image_bytes = f.read()

                    mime_type, _ = mimetypes.guess_type(uploaded_file.name)
                    if not mime_type:
                        mime_type = "image/jpeg"

                    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
                    image_payload = [{
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded_image}",
                            "detail": "high"
                        }
                    }]

                    # 🧠 AI Call per image
                    ai_result = get_ai_prescription_with_image(**data, image_payloads=image_payload)
                    interpretation = ai_result.get('lab_image_interpretation', '')

                    uploaded_file.seek(0)
                    AiLabImageInterpretation.objects.create(
                        ai_prescription=prescription,
                        lab_images=uploaded_file,
                        interpretation_text=interpretation
                    )

                # ✅ Optional: Update AIPrescription with summary fields from the last image
                prescription.summary_of_findings = ai_result.get('summary', '')
                prescription.diagnosis = ai_result.get('diagnosis', '')
                prescription.medicines = ai_result.get('medicines', '')
                prescription.tests = ai_result.get('tests', '')
                prescription.advice = ai_result.get('advice', '')
                prescription.recommended_specialty = ai_result.get('recommended_specialty', '')
                prescription.warning_signs = ai_result.get('warning_signs', '')
                prescription.diet_chart = ai_result.get('diet_chart', '')
                prescription.raw_response = ai_result.get('raw_content', '')
                prescription.save()


                # Payment handling
                if invoice:
                    invoice.ai_prescription = prescription
                    invoice.save()
                    del request.session['ai_prescription_invoice_id']

                if free:
                    patient.free_ai_prescriptions_used += 1
                    patient.save()
                    AIPrescriptionPayment.objects.create(
                        patient=patient,
                        ai_prescription=prescription,
                        amount=0.0,
                        payment_status='free',
                        transaction_id='FREE',
                        used_for_prescription=True
                    )
                else:
                    payment.ai_prescription = prescription
                    payment.used_for_prescription = True
                    payment.save()

                return redirect('prescription:ai_prescription_detail', pk=prescription.pk)

    return render(request, 'prescription/create.html', {
        'form': form,
        'patient_form': patient_form,
        'patient_missing': patient_missing
    })



@login_required
def lab_image_interpretation_view(request):
    patient = request.user.patient_profile
    interpretation_results = []

    if request.method == "POST":
        uploaded_files = request.FILES.getlist('lab_files')
        captured_image_data = request.POST.get("captured_image")

        if not uploaded_files and not captured_image_data:
            messages.error(request, "Please upload a lab file or capture an image.")
            return redirect('prescription:lab_test_interpretation')

        # Handle uploaded files
        for uploaded_file in uploaded_files:
            with NamedTemporaryFile(delete=False, suffix=".tmp") as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name

            with open(tmp_path, "rb") as f:
                image_bytes = f.read()

            mime_type, _ = mimetypes.guess_type(uploaded_file.name)
            if not mime_type:
                mime_type = "image/jpeg"

            encoded_image = base64.b64encode(image_bytes).decode("utf-8")

            image_payload = [{
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{encoded_image}",
                    "detail": "high"
                }
            }]

            interpretation_text = interpret_lab_images_only(
                image_payloads=image_payload,
                gender=patient.gender
            )

            uploaded_file.seek(0)
            result = AiLabImageInterpretation.objects.create(
                ai_prescription=None,
                patient=patient,
                lab_images=uploaded_file,
                interpretation_text=interpretation_text
            )
            interpretation_results.append(result)

        # Handle captured image
        if captured_image_data and captured_image_data.startswith("data:image"):
            try:
                format, imgstr = captured_image_data.split(';base64,')
                ext = format.split('/')[-1]
                file_data = ContentFile(base64.b64decode(imgstr), name=f"captured_lab.{ext}")

                image_payload = [{
                    "type": "image_url",
                    "image_url": {
                        "url": f"{captured_image_data}",
                        "detail": "high"
                    }
                }]

                interpretation_text = interpret_lab_images_only(
                    image_payloads=image_payload,
                    gender=patient.gender
                )

                result = AiLabImageInterpretation.objects.create(
                    ai_prescription=None,
                    patient=patient,
                    lab_images=file_data,
                    interpretation_text=interpretation_text
                )
                interpretation_results.append(result)

            except Exception as e:
                messages.warning(request, f"Could not interpret captured image: {e}")


        messages.success(request, "AI interpretation completed.")
        return render(request, 'labtest/ai_lab_results.html', {
            'results': interpretation_results
        })
    return render(request, 'labtest/ai_lab_test_file_upload.html')



@login_required
def lab_interpretation_history(request):
    patient = request.user.patient_profile
    interpretations = AiLabImageInterpretation.objects.filter(patient=patient).order_by('-created_at')  # or your timestamp field
    
    return render(request, 'labtest/interpretation_history.html', {
        'interpretations': interpretations
    })


#========================================================================================
def extract_section(text, pattern, fallback=""):
    try:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else fallback
    except Exception:
        return fallback



@login_required
def ai_prescription_detail(request, pk):
    prescription = AIPrescription.objects.filter(pk=pk).first()
    if not prescription:
        raise Http404("AI Prescription not found.")
    # Access check
    if prescription.user == request.user:
        pass
    elif prescription.bookings.filter(doctor__user=request.user).exists():
        pass
    else:
        raise PermissionDenied("You do not have permission to view this AI prescription.")
    # Extract diet_chart if missing
    diet_chart = prescription.diet_chart
    if not diet_chart or diet_chart.strip().lower() == "none":
        pattern = r"7\.\s*\**Suggested Diet Chart.*?\**:?\s*([\s\S]*?)(?=\n\d+\.\s|\Z)"
        extracted = extract_section(prescription.raw_response or "", pattern, fallback="None")
        if extracted and extracted.strip().lower() != "none":
            prescription.diet_chart = extracted
            prescription.save(update_fields=['diet_chart'])
            diet_chart = extracted
    lab_images_with_interpretation = prescription.ai_lab_test.all()
    return render(request, 'prescription/detail.html', {
        'prescription': prescription,
        'normalized_duration': normalize_duration_text(prescription.duration),
        'lab_images_with_interpretation': lab_images_with_interpretation,
        'diet_chart': diet_chart,
    })




@login_required
def ai_prescription_detail2(request, pk):
    prescription = get_object_or_404(AIPrescription, pk=pk,user=request.user)
    if prescription.user == request.user:
        pass
    elif prescription.bookings.filter(doctor__user=request.user).exists():
        pass
    else:
        raise PermissionDenied("You do not have permission to view this AI prescription.")    
  
    lab_images_with_interpretation = prescription.ai_lab_test.all()
  
    return render(request, 'prescription/detail.html', 
        {
        'prescription': prescription,   
        'normalized_duration':normalize_duration_text(prescription.duration),
        'lab_images_with_interpretation': lab_images_with_interpretation,
        })







@login_required
def ai_prescription_list(request):
    prescriptions = AIPrescription.objects.filter(user=request.user.id).order_by('-created_at')   
    datas = prescriptions
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for prescription in page_obj:
        prescription.normalized_duration = normalize_duration_text(prescription.duration)
    return render(request, 'prescription/ai_prescription_list.html', {'prescriptions': prescriptions,'page_obj':page_obj})




def ai_prescription_pdf(request, pk):
    prescription = AIPrescription.objects.get(pk=pk)
    diet_chart = prescription.diet_chart
    if not diet_chart or diet_chart.strip().lower() == "none":
        pattern = r"7\.\s*\**Suggested Diet Chart.*?\**:?\s*([\s\S]*?)(?=\n\d+\.\s|\Z)"
        extracted = extract_section(prescription.raw_response or "", pattern, fallback="None")
        if extracted and extracted.strip().lower() != "none":
            prescription.diet_chart = extracted
            prescription.save(update_fields=['diet_chart'])
            diet_chart = extracted

    template = get_template('prescription/prescription_pdf.html')  # Use a dedicated PDF template
    html = template.render({'prescription': prescription,'diet_chart': diet_chart})

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Prescription_{prescription.id}.pdf"'

    # Create PDF
    pisa_status = pisa.CreatePDF(src=html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


@login_required
def book_doctor(request, pk):
    try:
        prescription = AIPrescription.objects.get(pk=pk, user=request.user)
    except AIPrescription.DoesNotExist:
        messages.error(request, "You do not have permission to book a doctor for this prescription.")
        return redirect('prescription:home') 

    raw_specialty = (prescription.recommended_specialty or "").strip()

    # Match words like "Neurologist", "Cardiologist", "General Physician"
    specialties = re.findall(r'[A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*', raw_specialty)
    if not specialties and raw_specialty:
        specialties = [raw_specialty]

    query = Q()
    for term in specialties:
        query |= Q(specialization__icontains=term)

    available_doctors = Doctor.objects.filter(query) if specialties else Doctor.objects.none()

    return render(request, 'prescription/book_doctor.html', {
        'prescription': prescription,
        'available_doctors': available_doctors,
    })



@login_required
def create_patient_profile(request):
    try:
        existing = request.user.patient_profile
        messages.info(request, "You already have a patient profile.")
        return redirect('home')  # or wherever you want to go
    except Patient.DoesNotExist:
        pass

    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.user = request.user
            patient.save()
            messages.success(request, "✅ Patient profile created successfully.")
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')  # fallback
    else:
        form = PatientForm()

    next_url = request.GET.get('next', '')
    return render(request, 'patient/create_profile.html', {'form': form, 'next': next_url})





#========================== Speciliazed doctor consultation/booking/appointment =============


from uuid import uuid4
@login_required
def initiate_book_doctor_direct_payment(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = None

    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.warning(request, "Only patients can book doctors. Please create a patient profile first.")
        return redirect(f"{reverse('prescription:create_patient_profile')}?next={request.path}")

    if not is_payment_enabled_for_tenant(request.tenant):
        return redirect('prescription:book_doctor_direct', pk=doctor_id)

    invoice = create_payment_invoice(
        patient=patient,
        invoice_type='direct-consultation',
        amount=doctor.consultation_fees,
        description='Consultation fee for doctor',  # human-readable only
        related_object_id=doctor.id,
        doctor=doctor,
        doctor_booking=None,
    )


    request.session['doctor_booking_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')

#===========================================================================================



@login_required
def book_doctor_direct(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    user = request.user
    patient = None
    invoice=None
    form = DirectDoctorBookingForm()

    try:
        patient = user.patient_profile
    except Patient.DoesNotExist:
        return redirect(f"{reverse('prescription:create_patient_profile')}?next={request.path}")

    symptom_image = None
    symptom_video = None
     #=========================================================================================
    invoice_id = request.session.get('doctor_booking_invoice_id')             
    invoice = None
    if invoice_id:
        try:
            invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='direct-consultation')
        except PaymentInvoice.DoesNotExist:
            messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
            return redirect('prescription:doctor_bookings_list')
    #===============================================================================================

    if request.method == 'POST':
        form = DirectDoctorBookingForm(request.POST, request.FILES)
        if form.is_valid(): 
            duration = form.cleaned_data['duration']
            symptom_summary = form.cleaned_data['symptoms_summary']
            vital_signs = form.cleaned_data['vital_signs']

            captured_image_data = request.POST.get('captured_image')
            if captured_image_data:
                try:
                    format, imgstr = captured_image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    symptom_image = ContentFile(base64.b64decode(imgstr), name=f"captured_symptom.{ext}")
                except Exception:
                    messages.error(request, "Failed to process captured image.")

            recorded_video_data = request.POST.get('recorded_video')
            if recorded_video_data:
                try:
                    format, videostr = recorded_video_data.split(';base64,')
                    ext = format.split('/')[-1]
                    symptom_video = ContentFile(base64.b64decode(videostr), name=f"captured_video.{ext}")
                except Exception:
                    messages.error(request, "Failed to process recorded video.")
      
            booking = DoctorBooking.objects.create(
                patient=patient,
                doctor=doctor,
                ai_prescription=None,
                user=request.user,
                preferred_time=timezone.now(),
                symptom_image=symptom_image,
                symptom_video=symptom_video,
                symptoms_summary=symptom_summary,
                duration=duration,
                age=patient.age,
                medical_history=patient.medical_history,
                allergies=patient.allergies,
                current_medications=patient.current_medications,
                vital_signs=vital_signs,
                
            )
            #===================== upload labtest or old prescription ===========
            lab_files = request.FILES.getlist('lab_files')
            for file in lab_files:
                LabResultFile.objects.create(
                    main_booking=booking,
                    uploaded_by=request.user,
                    file=file
                )
            #=====================================================================
            if invoice:
                    invoice.doctor_booking = booking
                    invoice.save()
                    del request.session['doctor_booking_invoice_id']
            #================================================================

            messages.success(request, "Booking confirmed.")
            message = f"You have a new consultation booking from {patient.full_name}. Please check your dashboard."
            send_sms(tenant=request.tenant, phone_number=doctor.phone, message=message)
            create_notification(request.user, notification_type='Doctor booking msg', message=message, patient=patient, doctor=doctor)
            return redirect('prescription:doctor_bookings_list')  

    else:
        form = DirectDoctorBookingForm()
    return render(request, 'prescription/confirm_booking_direct.html', {'doctor': doctor, 'form': form,'patient':patient})





#=====================================================================================

@login_required
def initiate_confirm_booking_payment(request, prescription_id, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    patient = None
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        messages.warning(request, "Only patients can book doctors. Please create a patient profile first.")
        return redirect(f"{reverse('prescription:create_patient_profile')}?next={request.path}")


    description = f"confirm_booking:prescription={prescription_id};doctor={doctor_id};uid={uuid4().hex[:6]}"

    if not is_payment_enabled_for_tenant(request.tenant):
        return redirect('prescription:confirm_booking', prescription_id, doctor_id)

    invoice = create_payment_invoice(
        patient=patient,
        invoice_type='consultation',
        amount=doctor.consultation_fees,
        description=description,
        related_object_id=doctor.id,
        doctor_booking = None
    )
    request.session['doctor_booking_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')


#===============================================================================================





@login_required
def confirm_booking(request, prescription_id, doctor_id):
    prescription = get_object_or_404(AIPrescription, pk=prescription_id, user=request.user)
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    patient = prescription.patient
    invoice =None
    payment_amount = doctor.consultation_fees

    if not patient:
        messages.error(request, "No patient information found in this prescription. Cannot proceed with booking.")
        return redirect('prescription:ai_prescription_detail', pk=prescription.pk)
    
    #================== before creating - payment process need to trigger =====================


    if request.method == 'POST':
        symptom_image = request.FILES.get('symptom_image')
        symptom_video = request.FILES.get('symptom_video')  # In case it's uploaded as file

        # Handle base64 image capture
        if not symptom_image:
            captured_image_data = request.POST.get('captured_image')
            if captured_image_data:
                try:
                    format, imgstr = captured_image_data.split(';base64,')
                    ext = format.split('/')[-1]
                    symptom_image = ContentFile(base64.b64decode(imgstr), name=f"captured_symptom.{ext}")
                except Exception as e:
                    messages.error(request, "Failed to process captured image.")

        # Handle base64 recorded video
        if not symptom_video:
            recorded_video_data = request.POST.get('recorded_video')
            if recorded_video_data:
                try:
                    format, videostr = recorded_video_data.split(';base64,')
                    ext = format.split('/')[-1]
                    symptom_video = ContentFile(base64.b64decode(videostr), name=f"captured_video.{ext}")
                except Exception as e:
                    messages.error(request, "Failed to process recorded video.")
    #======================================================================================================
        if is_payment_enabled_for_tenant(request.tenant):
            invoice_id = request.session.get('doctor_booking_invoice_id')             
            invoice = None
            if invoice_id:
                try:
                    invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='consultation')
                except PaymentInvoice.DoesNotExist:
                    messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                    return redirect('prescription:doctor_bookings_list')
    #=======================================================================================================


        booking = DoctorBooking.objects.create(
            patient=patient,
            doctor=doctor,
            ai_prescription=prescription,
            user=request.user,
            preferred_time=timezone.now(),
            symptom_image=symptom_image,
            symptom_video=symptom_video,
            symptoms_summary=prescription.symptoms,
            duration=prescription.duration,
            age=prescription.age,
            medical_history=prescription.medical_history,
            allergies=prescription.allergies,
            current_medications=prescription.current_medications,
            vital_signs=prescription.vital_signs,
            location=prescription.location
        )
    #======================= lab test or old prescription uploading ====================
        lab_files = request.FILES.getlist('lab_files')
        for file in lab_files:
            LabResultFile.objects.create(
                main_booking=booking,
                uploaded_by=request.user,
                file=file
            )

   #========================================================================================
        if invoice:
            invoice.doctor_booking = booking
            invoice.save()
            del request.session['doctor_booking_invoice_id']
    #==============================================================================================

        messages.success(request, "Doctor appointment confirmed successfully.")
        message = f"You have a new consultation booking from {patient.full_name}. Please check your dashboard."
        send_sms(tenant=request.tenant, phone_number=doctor.phone, message=message)
        create_notification(request.user, notification_type='Doctor booking msg', message=message, patient=patient, doctor=doctor)
        return redirect('prescription:doctor_booking_success',doctor.id,booking.id)

    return render(request, 'prescription/confirm_booking.html', {
        'prescription': prescription,
        'doctor': doctor,
        'patient': patient
    })


def doctor_booking_success(request, doctor_id, booking_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    booking = get_object_or_404(DoctorBooking, id=booking_id, user=request.user)
    return render(request, 'prescription/booking_success.html', {
        'doctor': doctor,
        'booking': booking
    })





#==============================================================================
@login_required
def initiate_video_call_payment(request,booking_id):
    booking = get_object_or_404(DoctorBooking,id = booking_id)
    amount = booking.doctor.video_consultation_fees
    patient = booking.patient
    doctor = booking.doctor
   
    if not is_payment_enabled_for_tenant(request.tenant) or amount == 0:
        return redirect('prescription:request_video_call', booking_id)

    invoice = create_payment_invoice(
        patient=patient,
	doctor = doctor,
        invoice_type='video-consultation',
        amount=amount if amount else 0,
        description="Video consultation fees",       
        related_object_id=doctor.id,
        doctor_booking = booking
    )
    request.session['doctor_booking_video_call_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')
#===============================================================================================



@login_required
def request_video_call(request, booking_id):
    booking = get_object_or_404(DoctorBooking, id=booking_id)
    patient =None
    invoice =None
    doctor = booking.doctor

    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        messages.warning(request, 'Patient profile not found.')
        return redirect('prescription:home')

    if patient != booking.patient:
        messages.warning(request, 'Only the associated patient can access this follow-up booking.')
        return redirect('prescription:home')

    #=========================================================================
    if is_payment_enabled_for_tenant(request.tenant) and (doctor.video_consultation_fees or 0) > 0:   
        invoice_id = request.session.get('doctor_booking_video_call_invoice_id', None)
        invoice = None
        if invoice_id:
            try:
                invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='video-consultation')
            except PaymentInvoice.DoesNotExist:
                messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                return redirect('prescription:doctor_bookings_list')
        if not invoice:
            messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
            return redirect('prescription:doctor_bookings_list')

        if not invoice.is_paid:
            messages.warning(request, "Please complete payment before proceeding with video consultation.")
            return redirect('payment_gateway:review_invoice')

        #==============================================================================================

    if request.method == 'POST':
        form = RequestVideoCallForm(request.POST, instance=booking)
        if form.is_valid():
            form_instance = form.save(commit=False)
            form_instance.video_call_requested = True  # if you have a field to track this
            form_instance.save()
            if invoice:
                invoice.doctor_booking = booking
                invoice.save()   
                if 'doctor_booking_video_call_invoice_id' in request.session:
                    del request.session['doctor_booking_video_call_invoice_id']

            messages.success(request, 'Video call request submitted successfully.')
            message = f"You have a video consultation request from {patient.full_name}. Please check your dashboard."
            send_sms(tenant=request.tenant, phone_number=doctor.phone, message=message)
            create_notification(request.user, notification_type='Doctor video consultation booking msg', message=message, patient=patient, doctor=doctor)
            return redirect('finance:patient_dashboard')  # or wherever you want
        else:
            print(form.errors)
    else:
        form = RequestVideoCallForm(instance=booking)

    return render(request, 'prescription/request_video_call.html', {
        'form': form,
        'booking': booking
    })


def approve_request_video_call(request, booking_id):
    booking = get_object_or_404(DoctorBooking, id=booking_id)
    patient = booking.patient
    doctor = booking.doctor

    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.warning(request, 'Doctor profile not found.')
        return redirect('prescription:home')

    followup_doctor = booking.doctor
    if doctor != followup_doctor:
        messages.warning(request, 'Only the associated doctor can access this follow-up booking.')
        return redirect('prescription:home')

    if request.method == 'POST':
        form = ApproveRequestVideoCallForm(request.POST, instance=booking)
        if form.is_valid():
            form.save()
            text_message = f"Your video consultation with  {doctor.full_name}. Has been approved. Please check your dashboard."
            send_sms(tenant=request.tenant, phone_number=patient.phone, message=text_message)
            create_notification(request.user, notification_type='Doctor video consultation booking msg', message=text_message, patient=patient, doctor=doctor)
            return redirect('prescription:doctor_bookings_list')  # redirect after success
        else:
            print(form.errors)
    else:
        form = ApproveRequestVideoCallForm(instance=booking)
    return render(request, 'prescription/request_video_call_approve.html', {
        'form': form,
        'booking': booking
    })



@login_required
def doctor_bookings_list(request): 
    bookings = DoctorBooking.objects.filter().exclude(status='cancelled').order_by('-created_at')
    patient = None
    doctor = None
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        pass
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        pass
    if patient:
        bookings = bookings.filter(patient=patient)
    elif doctor:
        bookings = bookings.filter(doctor=doctor)
    else:
        bookings = DoctorBooking.objects.none()
        messages.warning(request, "You are not associated with any patient or doctor profile.")   

    datas =  bookings 
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 
    return render(request, 'prescription/bookings_list.html', {'bookings': bookings,'page_obj':page_obj})





@login_required
def doctor_booking_detail(request, pk):
    booking = get_object_or_404(DoctorBooking, pk=pk)

    is_doctor = booking.doctor and booking.doctor.user == request.user
    is_patient = booking.patient and booking.patient.user == request.user

    if not (is_doctor or is_patient):
        messages.warning(request,"You do not have permission to view this booking.")
        return redirect('prescription:doctor_bookings_list')

    return render(request, 'prescription/booking_detail.html', {'booking': booking})




PrescriptionFormSet = modelformset_factory(
    SuggestedMedicine,
    form=SuggestedMedicineForm,
    extra=1,
    can_delete=True,
)

from appointments.models import Appointment

@login_required
def create_doctor_prescription(request, booking_id, followup_id=None,appointment_id=None):
    booking = get_object_or_404(DoctorBooking, pk=booking_id)
    service_fee=None
    patient = booking.patient
    doctor = booking.doctor
    followup_booking = None
    appointment = None

    if appointment_id:
        appointment = get_object_or_404(Appointment, pk=appointment_id)

    if followup_id:
        followup_booking = get_object_or_404(DoctorFolloupBooking, pk=followup_id, doctor_booking=booking)

    ai_prescription = booking.ai_prescription if booking.ai_prescription else None

    if followup_booking:
        prescription_instance = None 
    else:
        prescription_instance = DoctorPrescription.objects.filter(
            ai_prescription=ai_prescription
        ).first()

    if booking.doctor.user != request.user:
        messages.error(request, "Only the assigned doctor can create a prescription for this booking.")
        return redirect('prescription:doctor_bookings_list')

    if request.method == 'POST':
        medical_form = DoctorPrescriptionForm(request.POST, request.FILES, instance=prescription_instance)
        prescription_formset = PrescriptionFormSet(request.POST, queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm(request.POST)

        if medical_form.is_valid() and prescription_formset.is_valid() and lab_test_form.is_valid():
            with transaction.atomic():
                doctor_prescription = medical_form.save(commit=False)
                doctor_prescription.patient = booking.patient
                doctor_prescription.doctor = booking.doctor
                doctor_prescription.ai_prescription = booking.ai_prescription if booking.ai_prescription else None
               
                if followup_booking:
                    doctor_prescription.booking_folloup_ref = followup_booking
                elif appointment:
                    doctor_prescription.appointment_ref = appointment
                else:
                    doctor_prescription.booking_ref = booking
                doctor_prescription.save()

                if followup_booking and booking.is_followup_valid():
                    service_fee = booking.doctor.folloup_consultation_fees
                else:
                   service_fee = booking.doctor.consultation_fees

                # Medicines
                for form in prescription_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        prescribed_medicine = form.save(commit=False)
                        prescribed_medicine.prescription = doctor_prescription
                        if not prescribed_medicine.medicine_name and prescribed_medicine.custom_medicine_name:
                            med_name = prescribed_medicine.custom_medicine_name.strip()
                            existing_medicine = Medicine.objects.filter(name__iexact=med_name).first()
                            if not existing_medicine:
                                new_medicine = Medicine.objects.create(
                                    name=med_name,
                                    user=request.user, 
                                    is_active=True,
                                )
                                prescribed_medicine.medicine_name = new_medicine
                        prescribed_medicine.save()

                # Lab Tests
                selected_lab_tests = request.POST.getlist('lab_tests')
                for test_id in selected_lab_tests:
                    try:
                        lab_test_catalog = LabTest.objects.get(id=test_id)
                        SuggestedLabTest.objects.create(
                            prescription=doctor_prescription,
                            lab_test_name=lab_test_catalog,
                            lab_test_notes='Pending'
                        )
                    except LabTest.DoesNotExist:
                        pass

                custom_tests_raw = request.POST.get('custom_lab_tests', '')
                custom_tests = re.split(r'[\n,]+|\s{2,}', custom_tests_raw)             
                custom_tests = [test.strip() for test in custom_tests if test.strip()]

                for test_name in custom_tests:
                    existing_test = LabTest.objects.filter(test_name__iexact=test_name).first()
                    if not existing_test:
                        new_test = LabTest.objects.create(
                            test_name=test_name.title(), 
                            test_type='Custom',      
                            price=0                      
                        )
                        lab_test_obj = new_test
                    else:
                        lab_test_obj = existing_test

                    SuggestedLabTest.objects.create(
                        prescription=doctor_prescription,
                        lab_test_name=lab_test_obj,
                        custom_lab_test_name=test_name
                    )


                if followup_booking:
                    followup_booking.status = 'completed'
                    followup_booking.save()
                elif appointment:
                    appointment.status = 'Completed'
                    appointment.save()
                else:
                    booking.status = 'completed'
                    booking.save()

                if followup_booking and hasattr(followup_booking, 'zoom_folloup_schedule'):
                    followup_booking.zoom_folloup_schedule.status = 'executed'
                    followup_booking.zoom_folloup_schedule.save()


                DoctorServiceLog.objects.create(
                    user=request.user,
                    ai_prescription=ai_prescription,
                    doctor=booking.doctor,
                    patient=booking.patient,
                    service_date=timezone.now(),
                    service_fee = service_fee
                )
                update_doctor_payment(booking.doctor)

                messages.success(request, 'Prescription created successfully.')
                text_message = f"Your prescription with  {doctor.full_name} completed. Please check your dashboard."
                send_sms(tenant=request.tenant, phone_number=patient.phone, message=text_message)
                create_notification(request.user, notification_type='Doctor Prescription readiness', message=text_message, patient=patient, doctor=doctor)
                return redirect('prescription:doctor_prescription_detail', pk=doctor_prescription.pk)

        # show errors if invalid
        return render(request, 'prescription/create_doctor_prescription.html', {
            'booking': followup_booking or booking,
            'medical_form': medical_form,
            'prescription_formset': prescription_formset,
            'lab_test_form': lab_test_form,
            'lab_tests': LabTest.objects.all(),
            'followup_booking':followup_booking
        })

    else:

        if followup_booking and not prescription_instance:
            last_prescription = DoctorPrescription.objects.filter(
                booking_ref=booking
            ).last()
            if last_prescription:
                medical_form = DoctorPrescriptionForm(
                   initial={
                    'diagnosis': last_prescription.diagnosis,
                    'advice': last_prescription.advice,

                  }
               )
            else:
                 medical_form = DoctorPrescriptionForm()
        else:
             medical_form = DoctorPrescriptionForm(instance=prescription_instance)       
        prescription_formset = PrescriptionFormSet(queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm()

    return render(request, 'prescription/create_doctor_prescription.html', {
        'booking': followup_booking or booking,
        'medical_form': medical_form,
        'prescription_formset': prescription_formset,
        'lab_test_form': lab_test_form,
        'lab_tests': LabTest.objects.all()
    })


@login_required
def doctor_prescription_list(request): 
    user = request.user
    doctor_pres_list = DoctorPrescription.objects.none()  # default empty queryset

    if hasattr(user, 'role'):
        if user.role == 'patient':
            try:
                patient = Patient.objects.get(user=user)
                doctor_pres_list = DoctorPrescription.objects.filter(patient=patient)
            except Patient.DoesNotExist:
                messages.warning(request, 'Patient profile not found.')
        elif user.role in ['doctor', 'consultant']:
            try:
                doctor = Doctor.objects.get(user=user)
                doctor_pres_list = DoctorPrescription.objects.filter(doctor=doctor)
            except Doctor.DoesNotExist:
                messages.warning(request, 'Doctor profile not found.')
        else:
            messages.warning(request, 'You are not authorized to view prescriptions.')
    else:
        messages.warning(request, 'Role information not available.')
    datas =  doctor_pres_list
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'prescription/doctor_prescription_list.html', {
        'doctor_pres_list': doctor_pres_list,
        'page_obj':page_obj
    })



from django.db import models
def doctor_prescription_detail(request, pk):
    prescription = get_object_or_404(DoctorPrescription, pk=pk)

    related_prescriptions = []

    if prescription.ai_prescription:
        # AI group
        related_prescriptions = DoctorPrescription.objects.filter(
            ai_prescription=prescription.ai_prescription
        ).order_by('prescribed_at')

    elif prescription.booking_ref:
        # Parent booking — include all follow-up prescriptions
        parent_booking = prescription.booking_ref
        related_prescriptions = DoctorPrescription.objects.filter(
            models.Q(booking_ref=parent_booking) |
            models.Q(booking_folloup_ref__doctor_booking=parent_booking)
        ).order_by('prescribed_at')

    elif prescription.booking_folloup_ref:
        # Follow-up booking — go back to parent
        parent_booking = prescription.booking_folloup_ref.doctor_booking
        related_prescriptions = DoctorPrescription.objects.filter(
            models.Q(booking_ref=parent_booking) |
            models.Q(booking_folloup_ref__doctor_booking=parent_booking)
        ).order_by('prescribed_at')

    else:
        related_prescriptions = [prescription]

    return render(request, 'prescription/doctor_prescription_detail.html', {
        'related_prescriptions': related_prescriptions,
        'main_prescription': prescription,
    })



@login_required
def doctor_prescription_detail_single(request, pk):
    prescription = get_object_or_404(DoctorPrescription, pk=pk)
    #medicines = prescription.pres_medicines.all()
    medicines = prescription.pres_medicines.select_related('medicine_name').all()
    lab_tests = prescription.lab_tests.all()

    return render(request, 'prescription/doctor_prescription_detail_single.html', {
        'prescription': prescription,
        'medicines': medicines,
        'lab_tests': lab_tests,
    })



def render_to_pdf(request, obj, template_path, filename_prefix, context):
    template = get_template(template_path)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{obj.id}.pdf"'

    pisa_status = pisa.CreatePDF(src=html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response



import qrcode
import base64
from io import BytesIO

def doctor_prescription_pdf(request, pk):
    prescription = DoctorPrescription.objects.get(pk=pk)
    qr = qrcode.make(f"https://prescription.aiha.live/prescription/prescription_single/{prescription.id}")
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()


    return render_to_pdf(
        request,
        prescription,
        'prescription/doctor_prescription_pdf.html',
        'doctor_Prescription',
        {
        'prescription': prescription,
        'qr_code_base64': img_str,
    }
    )



#================= folloup booking and soom meeting management =======================

import uuid

@login_required
def initiate_doctor_followup_booking_payment(request, doctor_booking_id):
    doctor_booking_instance = get_object_or_404(DoctorBooking, id=doctor_booking_id)
    if doctor_booking_instance and doctor_booking_instance.is_followup_valid():
        payment_amount = doctor_booking_instance.doctor.folloup_consultation_fees
    else:
        payment_amount = doctor_booking_instance.doctor.consultation_fees

    amount = payment_amount
    patient = doctor_booking_instance.patient
    doctor = doctor_booking_instance.doctor
    if not is_payment_enabled_for_tenant(request.tenant):
        return redirect('prescription:request_doctor_followup_booking', doctor_booking_id)

    invoice = create_payment_invoice(
        patient=patient,
        doctor=doctor,
        invoice_type='followup-consultation',
        amount=amount,
        description=f"followup-booking:{doctor_booking_instance.id}",
        related_object_id=doctor_booking_instance.id,
        doctor_followup_booking =None,
        doctor_booking=doctor_booking_instance
    )
    request.session['doctor_followup_booking_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')


def request_doctor_followup_booking(request, doctor_booking_id):
    doctor_booking_instance = get_object_or_404(DoctorBooking, id=doctor_booking_id)
    doctor = doctor_booking_instance.doctor
    patient = doctor_booking_instance.patient
    invoice =None

    if request.user != doctor_booking_instance.patient.user:
        messages.warning(request, 'Only associated patient can request for followup booking')
        return redirect('prescription:home')
    if doctor_booking_instance and doctor_booking_instance.is_followup_valid():
        payment_amount = doctor_booking_instance.doctor.folloup_consultation_fees
    else:
        payment_amount = doctor_booking_instance.doctor.consultation_fees

   #========================================================================================================

    if is_payment_enabled_for_tenant(request.tenant):
        invoice_id = request.session.get('doctor_followup_booking_invoice_id')             
        invoice = None
        if invoice_id:
            try:
                invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='followup-consultation')
            except PaymentInvoice.DoesNotExist:
                messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                return redirect('prescription:doctor_bookings_list')
        if not invoice.is_paid:
            messages.warning(request, "Please complete payment before proceeding with video consultation.")
            return redirect('payment_gateway:review_invoice') 
#====================================================================================================

    if request.method == "POST":
        form = DoctorFolloupBookingRequestForm(request.POST, request.FILES)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.doctor_booking = doctor_booking_instance
            booking.user = request.user

            captured_image_data = request.POST.get('captured_image')
            if captured_image_data:
                format, imgstr = captured_image_data.split(';base64,')  # format ~= data:image/png
                ext = format.split('/')[-1]
                img_file = ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")
                booking.symptom_image = img_file

            recorded_video_data = request.POST.get('recorded_video')
            if recorded_video_data:
                format, vidstr = recorded_video_data.split(';base64,')
                ext = format.split('/')[-1]
                vid_file = ContentFile(base64.b64decode(vidstr), name=f"{uuid.uuid4()}.{ext}")
                booking.symptom_video = vid_file
            booking.approved_followup_datetime = timezone.now()
            booking.proposed_followup_datetime = timezone.now()
            booking.status = 'confirmed'
            booking.save()
 	   #===================== upload lab test result if any ===============
            lab_files = request.FILES.getlist('lab_files')
            for file in lab_files:
                LabResultFile.objects.create(
                    followup_booking=booking,
                    uploaded_by=request.user,
                    file=file
                )
            #=========================================================
            if invoice:
                invoice.doctor_followup_booking = booking
                invoice.save()
                del request.session['doctor_followup_booking_invoice_id']
            #==========================================================
            text_message= f'You have followup booking request with {patient.full_name}, Please check your dashboard'
            send_sms(tenant=request.tenant, phone_number=doctor.phone, message= text_message)
            create_notification(request.user, notification_type='Doctor followup booking msg', message=text_message, patient=patient, doctor=doctor)
            #return redirect("prescription:followup_up_booking_request_list")
            return redirect("prescription:all_follow_up_schedules",doctor_booking_instance.id)
    else:
        form = DoctorFolloupBookingRequestForm()
    
    return render(request, "telemedicine/request_doctor_followup_booking.html", {
        "form": form,
        "doctor_booking": doctor_booking_instance
    })


def followup_up_booking_request_list(request):
    followup_requests = DoctorFolloupBooking.objects.all()
    doctor=None
    patient = None
    try:
        patient = Patient.objects.get(user=request.user)               
    except Patient.DoesNotExist:
        print('no patient')
    try:
        doctor = Doctor.objects.get(user=request.user)               
    except Doctor.DoesNotExist:
        print('no doctor')       

    if doctor:
        followup_requests = followup_requests.filter( doctor_booking__doctor=doctor)
    if patient:
        followup_requests = followup_requests.filter( doctor_booking__patient=patient)

    paginator = Paginator(followup_requests, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request,'telemedicine/doctor_followup_booking_request_list.html',{'page_obj':page_obj})




def aprove_doctor_followup_booking(request, followup_booking_id):
    followup_booking = get_object_or_404(DoctorFolloupBooking, id=followup_booking_id)
    patient=followup_booking.doctor_booking.patient
    doctor =None
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.warning(request, 'Doctor profile not found.')
        return redirect('prescription:home')
    followup_doctor = followup_booking.doctor_booking.doctor
    if doctor != followup_doctor:
        messages.warning(request, 'Only the associated doctor can access this follow-up booking.')
        return redirect('prescription:home')
    

    form = DoctorFolloupBookingApprovedForm()
    if request.method == "POST":
        form = DoctorFolloupBookingApprovedForm(request.POST, instance=followup_booking)
        if form.is_valid():
            form = form.save(commit=False)
            form.status = "confirmed"
            form.save()
            text_message= f'Your followup booking with {doctor.full_name}, Please check your dashboard'
            send_sms(tenant=request.tenant, phone_number=patient.phone, message= text_message)
            create_notification(request.user, notification_type='Doctor followup booking msg', message=text_message, patient=patient, doctor=doctor)
            #return redirect("prescription:followup_up_booking_request_list")
            return redirect("prescription:all_follow_up_schedules",followup_booking.doctor_booking.id)

    else:
        form = DoctorFolloupBookingApprovedForm(instance=followup_booking)
    return render(request, "telemedicine/approve_doctor_followup_booking.html", {"form": form, "booking":followup_booking})



@login_required
def doctor_followup_booking_detail(request, pk):
    booking = get_object_or_404( DoctorFolloupBooking, pk=pk)   
    is_doctor = booking.doctor_booking.doctor and booking.doctor_booking.doctor.user == request.user
    is_patient = booking.doctor_booking.patient and booking.doctor_booking.patient.user == request.user
    if not (is_doctor or is_patient):
        messages.warning(request,"You do not have permission to view this booking.")
        return redirect('prescription:doctor_bookings_list')
    return render(request, 'prescription/followup_booking_detail.html', {'booking': booking})



@login_required
def followup_prescription_detail_single(request, followup_id):
    followup = get_object_or_404(DoctorFolloupBooking, pk=followup_id)
    prescription = DoctorPrescription.objects.filter(booking_folloup_ref=followup).first()
    if not prescription:
        messages.error(request, "No prescription found for this follow-up booking.")
        return redirect('prescription:doctor_prescription_list')

    # Fetch medicines and lab tests
    medicines = SuggestedMedicine.objects.filter(prescription=prescription)
    lab_tests = SuggestedLabTest.objects.filter(prescription=prescription)

    return render(request, 'prescription/followup_prescription_detail_single.html', {
        'prescription': prescription,
        'followup': followup,
        'medicines': medicines,
        'lab_tests': lab_tests,
    })




def render_to_followup_pdf(request, obj, template_path, filename_prefix, context):
    template = get_template(template_path)
    html = template.render(context)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename_prefix}_{obj.id}.pdf"'

    pisa_status = pisa.CreatePDF(src=html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


def doctor_followup_prescription_pdf(request, pk):
    prescription = DoctorPrescription.objects.get(pk=pk)
    return render_to_followup_pdf(
        request,
        prescription,
        'prescription/doctor_followup_prescription_pdf.html',
        'doctor_Prescription',
        {'prescription': prescription}
    )


@login_required
def all_follow_up_schedules(request, booking_id): 
    doctor_booking = get_object_or_404(DoctorBooking, id=booking_id)

    user = request.user
    is_doctor = Doctor.objects.filter(user=user).exists()
    is_patient = Patient.objects.filter(user=user).exists()

    if is_doctor:
        doctor = Doctor.objects.get(user=user)
        if doctor_booking.doctor != doctor:
            raise PermissionDenied("You do not have permission to view this booking.")
    elif is_patient:
        patient = Patient.objects.get(user=user)
        if doctor_booking.patient != patient:
            raise PermissionDenied("You do not have permission to view this booking.")
    else:
        raise PermissionDenied("Access denied.")

    # Get follow-up bookings
    all_followup_requests = doctor_booking.doctor_folloup_bookings.all()

    # Paginate
    paginator = Paginator(all_followup_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'telemedicine/all_followup_requestes.html', {'page_obj': page_obj})

#======================================================================================

@login_required
def initiate_followup_video_consultation_payment(request, followup_booking_id):   
    followup_booking_instance = get_object_or_404(DoctorFolloupBooking, id=followup_booking_id)
    doctor = followup_booking_instance.doctor_booking.doctor
    amount = doctor.video_consultation_fees
    patient = followup_booking_instance.doctor_booking.patient
    doctor_booking = followup_booking_instance.doctor_booking

    if not is_payment_enabled_for_tenant(request.tenant) or amount == 0:
        return redirect('prescription:request_zoom_meeting',followup_booking_id)

    invoice = create_payment_invoice(
        patient=patient,
        doctor=doctor,
        invoice_type='followup-video-consultation',
        amount=amount,
        description=f"followup_video_consultation:{followup_booking_instance.id}",
        related_object_id=followup_booking_instance.id,
        zoom_meeting =None,
        doctor_booking=doctor_booking,
        #doctor_followup_booking =followup_booking_instance 

    )
    request.session['followup-video-consultation_invoice_id'] = invoice.id
    return redirect(reverse('payment_gateway:review_invoice') + f'?tran_id={invoice.tran_id}')

#==============================================================================================


def request_zoom_meeting(request, followup_booking_id):
    followup_booking_instance = get_object_or_404(DoctorFolloupBooking, id=followup_booking_id)
    doctor = followup_booking_instance.doctor_booking.doctor
    patient = followup_booking_instance.doctor_booking.patient
    invoice =None

    if request.user != followup_booking_instance.doctor_booking.patient.user:
        messages.warning(request, 'Only the associated patient can request a video conference.')
        return redirect('prescription:home')

#========================================================================================================
    if is_payment_enabled_for_tenant(request.tenant) and (doctor.video_consultation_fees or 0) > 0:
        invoice_id = request.session['followup-video-consultation_invoice_id']
        invoice = None
        if invoice_id:
            try:
                invoice = PaymentInvoice.objects.get(id=invoice_id, patient=patient, invoice_type='followup-video-consultation')
            except PaymentInvoice.DoesNotExist:
                messages.warning(request, "Invoice not found or expired. Please initiate payment again.")
                return redirect('prescription:doctor_bookings_list')
        if not invoice.is_paid:
            messages.warning(request, "Please complete payment before proceeding with video consultation.")
            return redirect('payment_gateway:review_invoice') 
#====================================================================================================


    if request.method == "POST":
        form = PatientZoomRequestForm(request.POST)
        if form.is_valid():
            zoom_meeting = form.save(commit=False)
            zoom_meeting.doctor_booking = followup_booking_instance.doctor_booking
            zoom_meeting.doctor_folloup_booking = followup_booking_instance
            zoom_meeting.user = request.user
            zoom_meeting.proposed_meeting_datetime = timezone.now()
            zoom_meeting.save()
           #=========================================================
            if invoice:
                invoice.zoom_meeting = zoom_meeting
                invoice.save()
                del request.session['followup-video-consultation_invoice_id'] 
            #==========================================================
            text_message= f'You have video consultation request with {patient.full_name}, Please check your dashboard'
            send_sms(tenant=request.tenant, phone_number=doctor.phone, message= text_message)
            create_notification(request.user, notification_type='Doctor video consultation booking msg', message=text_message, patient=patient, doctor=doctor)
            return redirect("prescription:doctor_bookings_list")
    else:
        form = PatientZoomRequestForm(
            initial={
                'doctor_folloup_booking': followup_booking_instance,
            }
        )

    return render(request, "telemedicine/request_zoom_meeting.html", {
        "form": form,
        'followup_booking_instance': followup_booking_instance
    })


def zoom_meeting_request_list(request):
    zoom_meeting_requests = ZoomMeeting.objects.all()
    doctor = Doctor.objects.filter(user = request.user).first()
    patient = Patient.objects.filter(user = request.user).first()
    if doctor:
        zoom_meeting_requests=  zoom_meeting_requests.filter( doctor_booking__doctor=doctor)
    if patient:
        zoom_meeting_requests = zoom_meeting_requests.filter( doctor_booking__patient=patient)

    paginator = Paginator(zoom_meeting_requests, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request,'telemedicine/zoom_meeting_request_list.html',{'page_obj': page_obj})



def approve_zoom_meeting(request, zoom_booking_id):
    zoom_booking = get_object_or_404(ZoomMeeting, id=zoom_booking_id)
    doctor =None
    patient = zoom_booking.doctor_booking.patient
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        messages.warning(request, 'Doctor profile not found.')
        return redirect('prescription:home')
    followup_doctor = zoom_booking.doctor_booking.doctor
    if doctor != followup_doctor:
        messages.warning(request, 'Only the associated doctor can access this follow-up booking.')
        return redirect('prescription:home')


    form = DoctorZoomScheduleForm()
    if request.method == "POST":
        form = DoctorZoomScheduleForm(request.POST, instance=zoom_booking)
        if form.is_valid():
            form = form.save(commit=False)
            form.status = "approved"
            form.save()
            text_message= f'Your followup video consultation with {doctor.full_name} has approved, Please check your dashboard'
            send_sms(tenant=request.tenant, phone_number=patient.phone, message= text_message)
            create_notification(request.user, notification_type='Doctor video consultation booking approval', message=text_message, patient=patient, doctor=doctor)
            return redirect("prescription:doctor_bookings_list")
    else:
        form = DoctorZoomScheduleForm(instance=zoom_booking)
    return render(request, "telemedicine/approve_zoom_meeting.html", {"form": form, "booking": zoom_booking})




def all_follow_up_zoom_schedules(request,booking_id):
    doctor_booking = get_object_or_404(DoctorBooking,id=booking_id)
    all_followup_requests = doctor_booking.zoom_schedules.all()

    paginator = Paginator(all_followup_requests, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request,'telemedicine/all_followup_zoom_requestes.html',{'page_obj':page_obj})



# this video was intended to match prescribing and video call in same page but not success
@login_required
def video_consultation_prescription(request, booking_id):
    booking = get_object_or_404(DoctorBooking, pk=booking_id)

    if not booking.video_link:
        try:
            zoom_meeting = create_zoom_meeting(doctor_email=booking.doctor.email)
            booking.video_link = zoom_meeting["join_url"]
            booking.save()
        except Exception as e:
            print("Zoom creation failed:", e)



    ai_prescription = booking.ai_prescription
    prescription_instance = DoctorPrescription.objects.filter( ai_prescription=ai_prescription).first()

    medical_form = DoctorPrescriptionForm(request.POST, request.FILES,instance= prescription_instance)
    prescription_formset = PrescriptionFormSet(request.POST, queryset=SuggestedMedicine.objects.none())
    lab_test_form = SuggestedLabTestForm(request.POST)
   
   
    booking = get_object_or_404(DoctorBooking, pk=booking_id)
    ai_prescription = booking.ai_prescription
    prescription_instance = DoctorPrescription.objects.filter(ai_prescription=ai_prescription).first()

    if booking.doctor.user != request.user:
        messages.error(request, "Only the assigned doctor can create a prescription for this booking.")
        return redirect('prescription:doctor_booking_detail', pk=booking_id)

    if request.method == 'POST':
        print('post/get=', request.method)
        medical_form = DoctorPrescriptionForm(request.POST, request.FILES,instance= prescription_instance)
        prescription_formset = PrescriptionFormSet(request.POST, queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm(request.POST)

        if medical_form.is_valid() and prescription_formset.is_valid() and lab_test_form.is_valid():           
            with transaction.atomic():
                doctor_prescription = medical_form.save(commit=False)
                doctor_prescription.patient = booking.patient
                doctor_prescription.doctor = booking.doctor
                doctor_prescription.ai_prescription = booking.ai_prescription
                doctor_prescription.booking_ref = booking
                doctor_prescription.save()              

                for form in prescription_formset:
                    if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                        prescribed_medicine = form.save(commit=False)
                        prescribed_medicine.prescription = doctor_prescription
                        prescribed_medicine.save()
                    else:
                        print(form.errors)

                selected_lab_tests = request.POST.getlist('lab_tests')
                if selected_lab_tests:                   

                    for test_id in selected_lab_tests:
                        try:
                            lab_test_catalog = LabTest.objects.get(id=test_id)

                            SuggestedLabTest.objects.create(
                                prescription=doctor_prescription,
                                 lab_test_name=lab_test_catalog,
                                 lab_test_notes='Pending'
                            )
                        except LabTest.DoesNotExist:
                            print(f"LabTestCatalog with ID {test_id} does not exist.")

                booking.status = 'completed'
                booking.save()
                DoctorServiceLog.objects.create(
                    user=request.user,
                    ai_prescription=ai_prescription if ai_prescription else None,
                    doctor=booking.doctor,
                    patient=booking.patient,
                    service_date=timezone.now()
                )
                messages.success(request, 'Prescription has been successfully created and is downloadable on the appointment list page')
                return redirect('prescription:doctor_prescription_detail', pk=doctor_prescription.pk)

        else:
            for form in prescription_formset:
                print("Form errors:", form.errors)

            return render(request, 'prescription/create_doctor_prescription.html', {
                'booking': booking,
                'medical_form': medical_form,
                'prescription_formset': prescription_formset,
                'lab_test_form': lab_test_form,
                'lab_tests':LabTest.objects.all(),
                 'video_link': booking.video_link,
            })

    else:
        medical_form = DoctorPrescriptionForm(instance= prescription_instance)
        prescription_formset = PrescriptionFormSet(queryset=SuggestedMedicine.objects.none())
        lab_test_form = SuggestedLabTestForm()

   

    return render(request, 'telemedicine/video_consultation_form.html', {
        'booking': booking,
        'medical_form': medical_form,
        'prescription_formset': prescription_formset,
        'lab_test_form': lab_test_form,
        'lab_tests': LabTest.objects.all(),
        'video_link': booking.video_link,
        
    })






@login_required
def manage_medicine(request, id=None):  
    instance = get_object_or_404(Medicine, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = MedicineForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('prescription:create_medicine') 

    datas = Medicine.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'medicine/add_medicine.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_medicine(request, id):
    instance = get_object_or_404(Medicine, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('prescription:create_medicine')

    messages.warning(request, "Invalid delete request!")
    return redirect('prescription:create_medicine')





@login_required
def manage_lab_test(request, id=None):  
    instance = get_object_or_404(LabTest, id=id) if id else None
    message_text = "updated successfully!" if id else "added successfully!"  
    form = LabTestForm(request.POST or None, request.FILES or None, instance=instance)

    if request.method == 'POST' and form.is_valid():
        form_intance=form.save(commit=False)
        form_intance.user = request.user
        form_intance.save()        
        messages.success(request, message_text)
        return redirect('prescription:create_lab_test') 

    datas = LabTest.objects.all().order_by('-created_at')
    paginator = Paginator(datas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'medicine/add_lab_test.html', {
        'form': form,
        'instance': instance,
        'datas': datas,
        'page_obj': page_obj
    })



@login_required
def delete_lab_test(request, id):
    instance = get_object_or_404(LabTest, id=id)
    if request.method == 'POST':
        instance.delete()
        messages.success(request, "Deleted successfully!")
        return redirect('prescription:create_lab_test') 

    messages.warning(request, "Invalid delete request!")
    return redirect('prescription:create_lab_test') 
