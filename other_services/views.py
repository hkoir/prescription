from django.shortcuts import render
from .models import NearbyService
from math import radians, sin, cos, sqrt, atan2



def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def nearby_service_list(request):
    services = []
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius = float(request.GET.get('radius', 10))
    service_type = request.GET.get('service_type', '').strip()

    user_lat = lat or ''
    user_lng = lng or ''

    if lat and lng:
        try:
            lat = float(lat)
            lng = float(lng)

            queryset = NearbyService.objects.all()
            if service_type:
                queryset = queryset.filter(service_type=service_type)

            for service in queryset:
                distance = haversine(lat, lng, service.latitude, service.longitude)
                if distance <= radius:
                  services.append({
                        'service': {
                            'name': service.name or '',
                            'latitude': service.latitude or 0,
                            'longitude': service.longitude or 0,
                            'address': service.address or 'N/A',
                            'contact_number': service.contact_number or 'N/A',
                            'service_type': service.get_service_type_display() or 'N/A',
                        },
                        'distance': round(distance, 2),
                    })



            services.sort(key=lambda x: x['distance'])

        except ValueError:
            pass

    return render(request, 'other_services/nearby_services_list.html', {
        'services': services,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'radius': radius,
        'service_type': service_type
    })









from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json



@ensure_csrf_cookie
def self_health_check(request):
    stress_questions = {
    '1': "Feeling nervous, anxious or on edge",
    '2': "Not being able to stop or control worrying",
    '3': "Worrying too much about different things",
    '4': "Trouble relaxing",
    '5': "Being so restless it's hard to sit still"
    }

    phq9_questions = {
        '1': "Little interest or pleasure in doing things",
        '2': "Feeling down, depressed, or hopeless",
        '3': "Trouble falling or staying asleep, or sleeping too much",
        '4': "Feeling tired or having little energy",
        '5': "Poor appetite or overeating",
        '6': "Feeling bad about yourself",
        '7': "Trouble concentrating on things",
        '8': "Moving or speaking slowly or being fidgety/restless",
        '9': "Thoughts of self-harm or suicide"
    }

    return render(request, "other_services/self_health_check.html",
        {'stress_questions':stress_questions,
        'phq9_questions':phq9_questions
         
         }
        )




@csrf_exempt   # for production remove and use CSRF tokens properly
@require_http_methods(["POST"])
def self_health_check_api(request):
    data = request.POST  # QueryDict
    response = {'ok': False, 'errors': []}
    errors = []
    result = {}

    def bad(msg):
        errors.append(str(msg))

    test = (data.get('test_type') or '').strip().lower()

    # helper: check all keys exist
    def has(*ks):
        return all(k in data for k in ks)

    # Parse helpers
    def to_int(key, default=None, minv=None, maxv=None):
        val = data.get(key)
        if val is None or val == '':
            return default
        try:
            v = int(float(val))
        except Exception:
            raise ValueError(f"Invalid integer for {key}")
        if (minv is not None and v < minv) or (maxv is not None and v > maxv):
            raise ValueError(f"{key} out of range")
        return v

    def to_float(key, default=None, minv=None, maxv=None):
        val = data.get(key)
        if val is None or val == '':
            return default
        try:
            v = float(val)
        except Exception:
            raise ValueError(f"Invalid number for {key}")
        if (minv is not None and v < minv) or (maxv is not None and v > maxv):
            raise ValueError(f"{key} out of range")
        return v

    # Use explicit test_type if provided (recommended)
    test = (data.get('test_type') or '').strip().lower()
    # helper to check keys quickly
    has = lambda *ks: all(k in data for k in ks)

    try:
        # ----- BMI -----
        if test == 'bmi' or (not test and has('weight', 'height') and not has('family_history','resting_hr','bp_sys','bp_dia')):
            try:
                weight = float(data.get('weight', 0))
                height_cm = float(data.get('height', 0))
                if weight <= 0 or height_cm <= 0:
                    return bad("Weight and height must be positive numbers.")
                height_m = height_cm / 100
                bmi = weight / (height_m ** 2)
                if bmi < 18.5:
                    status = "Underweight"
                elif bmi < 25:
                    status = "Normal weight"
                elif bmi < 30:
                    status = "Overweight"
                else:
                    status = "Obese"
                return JsonResponse({'ok': True, 'bmi': round(bmi, 1), 'bmi_status': status})
            except Exception:
                return bad("Invalid input for BMI check.")

      # ----- Heart Rate -----
        if test == 'heart' or (not test and has('resting_hr', 'age') and not has('weight', 'family_history')):
            try:
                resting_hr = int(data.get('resting_hr', 0))
                age = int(data.get('age', 0))
                after_walking_hr = data.get('after_walking_hr')

                if not (30 <= resting_hr <= 220):
                    return bad("Resting heart rate must be between 30 and 220.")
                if not (10 <= age <= 120):
                    return bad("Age must be between 10 and 120.")

                if after_walking_hr is not None:
                    after_walking_hr = int(after_walking_hr)
                    if not (30 <= after_walking_hr <= 220):
                        return bad("After walking heart rate must be between 30 and 220.")

                ideal_min, ideal_max = 60, 100
                after_walking_min, after_walking_max = 90, 130

                # Resting HR status
                resting_status = 'Normal'
                if resting_hr < ideal_min:
                    resting_status = 'Below Normal (Bradycardia)'
                elif resting_hr > ideal_max:
                    resting_status = 'Above Normal (Tachycardia)'

                after_walking_status = None
                if after_walking_hr is not None:       
                    after_walking_status = 'Normal'
                    if after_walking_hr < after_walking_min:
                        after_walking_status = 'Below Expected'
                    elif after_walking_hr > after_walking_max:
                        after_walking_status = 'Above Expected'

                return JsonResponse({
                    'ok': True,                   
                    'age': age,
                    'ideal_hr_min': ideal_min,
                    'ideal_hr_max': ideal_max,
                    'resting_hr': resting_hr,
                    'heart_status': resting_status,

                    'after_walking_hr_min': after_walking_min,
                    'after_walking_hr_max': after_walking_max,
                    'after_walking_hr': after_walking_hr,
                    'after_walking_status': after_walking_status
                })
            except Exception:
                return bad("Invalid input for heart rate check.")


        # ----- Stress -----
        if test == 'stress' or (not test and has('stress_q1','stress_q2','stress_q3','stress_q4','stress_q5')):
            try:
                scores = [int(data.get(f'stress_q{i}', 0)) for i in range(1,6)]
                if any(s < 0 or s > 4 for s in scores):
                    return bad("Stress question answers must be between 0 and 4.")
                total = sum(scores)
                if total <= 5:
                    status = "Low Stress"
                elif total <= 10:
                    status = "Moderate Stress"
                elif total <= 15:
                    status = "High Stress"
                else:
                    status = "Very High Stress"
                return JsonResponse({'ok': True, 'stress_level': total, 'stress_status': status})
            except Exception:
                return bad("Invalid input for stress check.")

        # ----- Blood Pressure -----
        if test == 'bp' or (not test and has('bp_sys', 'bp_dia')):
            try:
                sys = int(data.get('bp_sys', 0))
                dia = int(data.get('bp_dia', 0))
                if sys < 50 or sys > 250 or dia < 30 or dia > 150:
                    return bad("Blood pressure values out of normal range.")
                if sys < 120 and dia < 80:
                    category = "Normal"; advice = "Keep up healthy lifestyle."
                elif 120 <= sys < 130 and dia < 80:
                    category = "Elevated"; advice = "Adopt healthy lifestyle changes."
                elif (130 <= sys < 140) or (80 <= dia < 90):
                    category = "Hypertension Stage 1"; advice = "Consult doctor; monitor BP regularly."
                elif (140 <= sys) or (90 <= dia):
                    category = "Hypertension Stage 2"; advice = "Seek medical advice immediately."
                else:
                    category = "Consult Doctor"; advice = "Monitor your blood pressure."
                return JsonResponse({'ok': True, 'bp_category': category, 'bp_advice': advice})
            except Exception:
                return bad("Invalid input for blood pressure check.")

     
        # ----- Cholesterol -----
        if test == 'cholesterol' or (not test and has('total_chol','ldl','hdl','triglycerides')):
            try:
                total = float(data.get('total_chol', 0))
                ldl = float(data.get('ldl', 0))
                hdl = float(data.get('hdl', 0))
                tri = float(data.get('triglycerides', 0))
                if not(100 <= total <= 400 and 50 <= ldl <= 250 and 20 <= hdl <= 100 and 50 <= tri <= 500):
                    return bad("Cholesterol values out of range.")
                risk_score = 0
                if total > 240: risk_score += 2
                if ldl > 160: risk_score += 2
                if hdl < 40: risk_score += 2
                if tri > 200: risk_score += 2
                if risk_score <= 2:
                    risk = "Desirable"; advice = "Keep healthy lifestyle."
                elif risk_score <= 5:
                    risk = "Borderline High"; advice = "Consider diet and exercise changes."
                else:
                    risk = "High"; advice = "Consult doctor for treatment."
                return JsonResponse({'ok': True, 'cholesterol_risk': risk, 'cholesterol_advice': advice})
            except Exception:
                return bad("Invalid input for cholesterol check.")

        # ----- Sleep -----
        if test == 'sleep' or (not test and has('sleep_hours','difficulty_sleep','feel_rested','snoring')):
            try:
                hours = float(data.get('sleep_hours', 0))
                diff = data.get('difficulty_sleep', '')
                rested = data.get('feel_rested', '')
                snoring = data.get('snoring', '')
                if hours < 0 or hours > 24 or diff not in ['yes','no'] or rested not in ['yes','no'] or snoring not in ['yes','no']:
                    return bad("Invalid sleep input.")
                quality = "Good"; advice = "Keep good sleep hygiene."
                if hours < 6 or diff == 'yes' or rested == 'no':
                    quality = "Poor"; advice = "Consider sleep evaluation."
                if snoring == 'yes':
                    advice += " Snoring may indicate sleep apnea; consult doctor."
                return JsonResponse({'ok': True, 'sleep_quality': quality, 'sleep_advice': advice})
            except Exception:
                return bad("Invalid input for sleep quality check.")

        # ----- PHQ-9 -----
        if test == 'phq9' or (not test and all(f'phq9_q{i}' in data for i in range(1,10))):
            try:
                scores = [int(data.get(f'phq9_q{i}', 0)) for i in range(1,10)]
                if any(s < 0 or s > 3 for s in scores):
                    return bad("PHQ-9 answers must be between 0 and 3.")
                total = sum(scores)
                if total <= 4:
                    severity = "Minimal depression"; advice = "No treatment necessary."
                elif total <= 9:
                    severity = "Mild depression"; advice = "Watchful waiting; repeat assessment."
                elif total <= 14:
                    severity = "Moderate depression"; advice = "Consider counseling or medication."
                elif total <= 19:
                    severity = "Moderately severe depression"; advice = "Active treatment with meds and counseling."
                else:
                    severity = "Severe depression"; advice = "Immediate treatment recommended."
                return JsonResponse({'ok': True, 'phq9_severity': severity, 'phq9_advice': advice})
            except Exception:
                return bad("Invalid input for PHQ-9 check.")

        # ----- Activity -----
        if test == 'activity' or (not test and has('moderate_minutes','vigorous_minutes','sedentary_hours')):
            try:
                moderate = int(data.get('moderate_minutes', 0))
                vigorous = int(data.get('vigorous_minutes', 0))
                sedentary = float(data.get('sedentary_hours', 0))
                if moderate < 0 or vigorous < 0 or sedentary < 0 or sedentary > 24:
                    return bad("Invalid activity inputs.")
                total_activity = moderate + 2 * vigorous
                if total_activity >= 150 and sedentary <= 8:
                    level = "Active"; advice = "Good job maintaining activity."
                elif total_activity >= 75:
                    level = "Moderately Active"; advice = "Try to increase activity and reduce sitting time."
                else:
                    level = "Inactive"; advice = "Increase activity to reduce health risks."
                return JsonResponse({'ok': True, 'activity_level': level, 'activity_advice': advice})
            except Exception:
                return bad("Invalid input for physical activity check.")

        # ----- Hydration -----
        if test == 'hydration' or (not test and has('glasses_per_day','thirst_frequency')):
            try:
                glasses = int(data.get('glasses_per_day', 0))
                thirst = data.get('thirst_frequency', '')
                if glasses < 0 or glasses > 20 or thirst not in ['never','rarely','sometimes','often','very_often']:
                    return bad("Invalid hydration inputs.")
                if glasses >= 8 and thirst in ['never', 'rarely']:
                    status = "Well Hydrated"; advice = "Keep up the good hydration habits."
                elif glasses >= 5:
                    status = "Adequate Hydration"; advice = "Try to drink more water daily."
                else:
                    status = "Dehydrated"; advice = "Increase water intake to avoid health issues."
                return JsonResponse({'ok': True, 'hydration_status': status, 'hydration_advice': advice})
            except Exception:
                return bad("Invalid input for hydration check.")

        # nothing matched
        return bad("Invalid or incomplete data. Please check inputs.")

    except Exception as exc:
        # unexpected
        return bad("Unexpected server error: " + str(exc))
