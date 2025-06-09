
import re
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def get_ai_prescription(
    symptoms, duration, gender,
    medical_history=None, allergies=None, age=None,
    current_medications=None, vital_signs=None,
    body_weight=None, body_weight_unit=None,
    body_height=None, body_height_unit=None,
    location=None
):
    # Sanitize input defaults
    medical_history = medical_history or "No significant medical history"
    allergies = allergies or "No known drug allergies"
    current_medications = current_medications or "None"
    vital_signs = vital_signs or "Not available"
    body_weight = body_weight or "Not available"
    body_weight_unit = body_weight_unit or ""
    body_height = body_height or "Not available"
    body_height_unit = body_height_unit or ""
    age = age or "Not available"
    location = location or "Not specified"

    prompt = f"""
You are an experienced medical doctor.

Patient Details:
- Age: {age}
- Gender: {gender}
- Symptoms: {symptoms}
- Duration of symptoms: {duration} days
- Medical History: {medical_history}
- Allergies: {allergies}
- Current Medications: {current_medications}
- Vital Signs: {vital_signs}
- Body Weight: {body_weight} {body_weight_unit}
- Body Height: {body_height} {body_height_unit}
- Location: {location}

Please provide a structured response with these sections:

1. Diagnosis:
2. Recommended Medicines (format each line as: MedicineName Dosage, Frequency, Duration)
3. Necessary Lab Tests:
4. Medical Advice:
5. Recommended Specialist (e.g., Cardiologist, ENT, Dermatologist, General Physician). Only give the specialty name, do not skip:
6. Warning Signs requiring urgent attention:

Do not skip or merge any section. Always number each section clearly from 1 to 6.
"""

    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=800,
        extra_headers={
            "HTTP-Referer": "https://prescription.aiha.live",
            "X-Title": "PrescriptionApp"
        }
    )

    content = response.choices[0].message.content

    # Use flexible regex patterns to extract each section
    diagnosis = extract_section(content, r"1\.\s*\**Diagnosis\**:?(.*?)(?:2\.|\Z)", "N/A")
    medicines_text = extract_section(content, r"2\.\s*\**Recommended Medicines\**:?(.*?)(?:3\.|\Z)", "None")
    tests = extract_section(content, r"3\.\s*\**Necessary Lab Tests\**:?(.*?)(?:4\.|\Z)", "None")
    advice = extract_section(content, r"4\.\s*\**Medical Advice\**:?(.*?)(?:5\.|\Z)", "Follow general guidelines")
    #specialty_raw = extract_section(content, r"5\.\s*\**Recommended Specialist\**:?(.*?)(?:6\.|\Z)", "General Physician")
    warning_signs = extract_section(content, r"6\.\s*\**Warning Signs.*?\**:?(.*)", "None specified")
    recommended_specialty = extract_recommended_specialty_from_raw(content)


    return {
        "diagnosis": diagnosis.strip(),
        "medicines": parse_medicines(medicines_text),
        "tests": tests.strip(),
        "advice": advice.strip(),
        #"recommended_specialty": clean_specialty(specialty_raw),
	"recommended_specialty": recommended_specialty,
        "warning_signs": warning_signs.strip(),
        "raw_content": content
    }


def extract_section(text, pattern, fallback=""):
    try:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else fallback
    except Exception:
        return fallback


def clean_specialty(text):
    return text.strip().split("\n")[0].split(".")[0].strip()


def parse_medicines(medicines_text):
    medicines = []
    lines = medicines_text.strip().splitlines()

    for line in lines:
        line = line.strip("-* \n\t")
        if not line or line.lower().startswith("none") or "name" in line.lower():
            continue

        parts = re.split(r'[,\t]+', line)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 3:
            name_dosage = parts[0].rsplit(" ", 1)
            if len(name_dosage) == 2:
                name, dosage = name_dosage
            else:
                name, dosage = parts[0], ""
            frequency, duration = parts[1], parts[2]
        else:
            name = parts[0]
            dosage = frequency = duration = ""

        medicines.append({
            "name": name,
            "dosage": dosage,
            "frequency": frequency,
            "duration": duration,
        })

    return medicines




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


