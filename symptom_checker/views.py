from django.shortcuts import render, redirect, get_object_or_404
from .models import SymptomCheckSession, SymptomAnswer
from .ai import get_next_symptom_question, get_final_symptom_summary

from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from io import BytesIO

from django.shortcuts import render, get_object_or_404
from .models import SymptomCheckSession, SymptomAnswer
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect, get_object_or_404
from .models import SymptomCheckSession, SymptomAnswer

from .forms import SymptomSessionStartForm

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from datetime import date
from .models import SymptomCheckSession, SymptomAnswer
from .ai import get_next_symptom_question, get_final_symptom_summary

from prescription.models import Patient
from prescription.ai import get_ai_prescription
from prescription.models import AIPrescription
from finance.models import AIPrescriptionPayment
from django.contrib import messages
import re
from datetime import datetime
from datetime import timedelta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from symptom_checker.utils import translate_if_needed,translate_from_english,translate_to_english

MAX_QA_ROUNDS = 5
FREE_LIMIT = 5


from django.shortcuts import render
from django.views.generic import TemplateView

class DisclaimerView(TemplateView):
    template_name = 'legal/disclaimer.html'



def get_current_step(session, steps, total_steps):
    for idx, field in enumerate(steps, start=1):
        if not getattr(session, field):
            return idx
    return total_steps  # fallback



def calculate_age(dob):
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))




from.forms import SymptomCheckForm
from typing import Optional
from django.urls import reverse



@login_required
def start_symptom_check(request):     
    user = request.user   
    patient: Optional[Patient] = getattr(user, 'patient_profile', None)   

    if patient and patient.needs_profile_update():
        return redirect(f"{reverse('finance:update_patient_profile', args=[patient.id])}?next={request.path}")


    session, created = SymptomCheckSession.objects.get_or_create(user=user, is_completed=False)

    if request.method == "POST":
        form = SymptomCheckForm(request.POST, instance=session)
        if form.is_valid():
            session = form.save(commit=False)
            #weight,height,history,allergies,location
            if patient:
                session.gender = patient.gender
                session.dob = patient.dob
                session.age = patient.age
                session.weight_in_kg = patient.body_weight
                session.height_in_cm = patient.body_height
                session.medical_history = patient.medical_history
                session.allergies = patient.allergies
                session.location = patient.city

            session.is_completed = True
            session.save()
            return redirect("symptom_checker:symptom_chat", session_id=session.id)
    else:
        form = SymptomCheckForm(instance=session)

    return render(request, "symptom_checker/start.html", {"form": form})






def is_yes_no_question(question: str) -> bool:
    # Clean question
    question_clean = question.strip().lower()

    # Remove emoji/symbol/prefix decorations (e.g., "🩺 Ai health::")
    question_clean = re.sub(r'^[^\w]*[\w\s]*::\s*', '', question_clean)

    # Common yes/no question starters
    yes_no_starters = (
        "do ", "does ", "did ",
        "is ", "are ", "was ", "were ",
        "have ", "has ", "had ",'Have','Has','Had'
        "can ", "could ", "would ", "will ",
        "should ", "shall ",
    )

    if any(question_clean.startswith(start) for start in yes_no_starters):
        return True

    return any(phrase in question_clean for phrase in [
        "yes or no", "correct?", "right?", "is that true", "isn't it", "aren't you", "do you agree"
    ])




def symptom_chat(request, session_id):
    free_limit = 5
    session = get_object_or_404(SymptomCheckSession, id=session_id, user=request.user)
    user = request.user

    try:
        patient = user.patient_profile
    except Patient.DoesNotExist:
        patient = None

    # Get Q&A history
    history = session.answers.order_by('created_at')
    #qa_history = [{"question": ans.question.strip(), "answer": ans.answer.strip()} for ans in history]
    qa_history = [{"question": ans.question.strip(), "answer": translate_from_english(ans.answer.strip())} for ans in history]

    valid_answers = [qa for qa in qa_history if qa["question"] and qa["answer"]]

    # Handle POST for adding a question-answer pair
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        answer = request.POST.get("answer", "").strip()
        if question and answer:
            #SymptomAnswer.objects.create(session=session, question=question, answer=answer)                   
            translated_answer = translate_to_english(answer)
            SymptomAnswer.objects.create(session=session, question=question, answer=translated_answer)

            return redirect('symptom_checker:symptom_chat', session_id=session.id)

    # If all questions answered, process AI summary and prescription
    if len(valid_answers) >= MAX_QA_ROUNDS:
        # Generate AI Summary once
        if not session.ai_summary:
            result = get_final_symptom_summary(
                valid_answers,
                age=session.age,
                gender=session.gender,

                weight=session.weight_in_kg,
                height=session.height_in_cm,
                location=session.location
            )
            session.probable_disease = result.get("probable_disease")
            session.probable_symptoms = result.get("probable_symptoms")
            session.ai_summary = result.get("ai_summary")
            session.is_completed = True
            session.save()

        # Ensure patient object exists
        if not patient:
            patient = Patient.objects.create(
                user=user,
                full_name=user.username,
                dob=session.dob,
                gender=session.gender,
                body_weight=session.weight_in_kg,
                body_height=session.height_in_cm,
                address=session.location,
            )

        # Prepare text for AI prescription generation
        symptoms_text = "\n".join([f"{qa['question']}: {qa['answer']}" for qa in valid_answers])
        duration_guess = session.duration or '3 days' 
        

        # Generate AI Prescription
        ai_data = get_ai_prescription(
            symptoms=symptoms_text,
            duration=duration_guess,
            gender=session.gender,
            age=session.age,

            body_weight=session.weight_in_kg,
            body_weight_unit="kg",
            body_height=session.height_in_cm,
            body_height_unit="cm",

            location=session.location,
            medical_history=session.medical_history,
            allergies=session.allergies,
            current_medications=session.current_medications,

            vital_signs=session.vital_signs
        )

        # Save AI Prescription
        ai_prescription, created = AIPrescription.objects.get_or_create(
            session=session,
            defaults={
                'user': user,
                'patient': patient,
                'symptoms': session.probable_symptoms,                
                'duration': duration_guess,
                'age': patient.age,
                'gender': patient.gender,
                'medical_history': session.medical_history,
                'allergies': session.allergies,
                'current_medications': session.current_medications,
                'vital_signs': session.vital_signs,
                'location': session.location,
                'diagnosis': ai_data['diagnosis'],
                'medicines': ai_data['medicines'],
                'tests': ai_data['tests'],
                'advice': ai_data['advice'],
                'recommended_specialty': ai_data['recommended_specialty'],
                'warning_signs': ai_data.get('warning_signs', ''),
		'raw_response':ai_data["raw_content"]
            }
        )

        # Handle free vs paid usage
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
            free = False

        # Save payment info
        if free:
            patient.free_ai_prescriptions_used += 1
            patient.save()

            payment, created = AIPrescriptionPayment.objects.get_or_create(
                ai_prescription=ai_prescription,
                defaults={
                    "patient": patient,
                    "amount": 0.0,
                    "payment_status": 'free',
                    "transaction_id": 'FREE'
                }
            )

            if not created:
                payment.used_for_prescription = True
                payment.save()


        return render(request, 'symptom_checker/symptom_summary.html', {
            "session": session,
            "summary": session.ai_summary,
            "qa_history": valid_answers,
        })

    next_question = get_next_symptom_question(valid_answers)
    translated_question = translate_from_english(next_question)


    progress_percent = int((len(valid_answers) / MAX_QA_ROUNDS) * 100)
    yes_no = is_yes_no_question(next_question)


    return render(request, 'symptom_checker/question.html', {
        "session": session,
       # "question": next_question,
        "question": translated_question,
        "current_step": len(valid_answers) + 1,
        "total_steps": MAX_QA_ROUNDS,
        "progress_percent": progress_percent,
         "yes_no": yes_no,
    })





@login_required
def my_symptom_checks(request):
    sessions = SymptomCheckSession.objects.all().order_by('-created_at')
    return render(request, 'symptom_checker/session_list.html', {'sessions': sessions})







@login_required
def symptom_summary_view(request, session_id):
    session = get_object_or_404(SymptomCheckSession, id=session_id)
    raw_history = session.answers.order_by('created_at').values('question', 'answer')

    translated_history = []
    for item in raw_history:
        q = item["question"]
        a = item["answer"]
        translated_history.append({
            "question": translate_if_needed(q),
            "answer": translate_if_needed(a),
        })

    ai_prescription = getattr(session, 'ai_prescription', None)

    return render(request, 'symptom_checker/symptom_summary.html', {
        "session": session,
        'probable_disease':translate_if_needed(session.probable_disease),
        'probable_symptoms':translate_if_needed(session.probable_symptoms),
        "summary": translate_if_needed(session.ai_summary),
        "qa_history": translated_history,
        "ai_prescription": ai_prescription,
    })





def download_symptom_summary_pdf(request, session_id):
    session = get_object_or_404(SymptomCheckSession, id=session_id)

    if not session.ai_summary:
        messages.warning(request,'Symptom checker has not completed properly')
        return redirect('symptom_checker:my_symptom_checks')
        

    history = session.answers.order_by('created_at')
    qa_history = [{"question": ans.question, "answer": ans.answer} for ans in history]

    template = get_template("symptom_checker/summary_pdf.html")
    html = template.render({
        "session": session,
        "summary": session.ai_summary,
        "qa_history": qa_history,
    })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="symptom_summary_{session.id}.pdf"'

    pisa_status = pisa.CreatePDF(src=html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response




def delete_empty_sessions():
    cutoff = timezone.now() - timedelta(hours=10)
    SymptomCheckSession.objects.filter(ai_summary__isnull=True, answers__isnull=True, created_at__lt=cutoff).delete()
