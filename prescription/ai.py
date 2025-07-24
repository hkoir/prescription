
import re
import os
from openai import OpenAI
from deep_translator import GoogleTranslator


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


BN_RE = re.compile(r'[\u0980-\u09FF]')
BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
BN_DURATION_MAP = {"দিন": "days", "সপ্তাহ": "weeks", "মাস": "months", "বছর": "years"}


def is_bangla(text):
    return bool(text and BN_RE.search(text))

def translate_to_english(text):
    if not text:
        return "", "und"
    if not is_bangla(text):
        return text, "en"
    try:
        tr = GoogleTranslator(source="auto", target="en").translate(text)
        return tr, "bn"
    except Exception:
        return text, "bn"

def normalize_duration(raw):
    if not raw:
        return "Not available"
    txt = raw.strip().translate(BN_DIGITS)
    for bn, en in BN_DURATION_MAP.items():
        txt = txt.replace(bn, f" {en} ")
    return " ".join(txt.split())



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


    symptoms_en, _sym_lang   = translate_to_english(symptoms)
    medical_history_en, _    = translate_to_english(medical_history)
    allergies_en, _          = translate_to_english(allergies)
    current_meds_en, _       = translate_to_english(current_medications)
    vital_signs_en, _        = translate_to_english(vital_signs)
    location_en, _           = translate_to_english(location)

    # Duration normalization (handles Bangla numerals/units)
    duration_norm = normalize_duration(duration)


    prompt = f"""
You are an experienced medical doctor with expertise in [Country/Region] medications.

Please analyze the following patient data and provide a structured clinical response in the exact format described.

Patient Details:
- Age: {age}
- Gender: {gender}
- Symptoms: {symptoms_en}
- Duration of symptoms: {duration_norm}
- Medical History: {medical_history_en}
- Allergies: {allergies_en or "None"}
- Current Medications: {current_meds_en or "None"}
- Vital Signs: {vital_signs_en or "Not available"}
- Body Weight: {body_weight} {body_weight_unit}
- Body Height: {body_height} {body_height_unit}
- Location: {location_en or "Not specified"}

🧠 Please provide a **structured and clinically accurate response** in **this exact format**:

---

0. Summary of Findings:
- [2–3 line clinical overview: include significant symptoms, vitals, and red flags.]

1. Diagnosis:
- [Insert specific diagnosis or differential diagnosis.]

2. Recommended Medicines:
List each medicine **in the following exact structure**, one per line:
- Name: Paracetamol  
  Dosage: 500mg  
  Frequency: 1-1-1 (three times daily)  
  Duration: 5 days

- Name: Omeprazole  
  Dosage: 20mg  
  Frequency: 1-0-0 (once daily before food)  
  Duration: 7 days

⚠️ **Rules for Medicines:**
- Only suggest medicines that are commonly available in [Country/Region].
- Avoid suggesting steroids unless absolutely necessary.
- Use "as needed" for painkillers, anti-migraine, or rescue medications.
- Always specify dosage, frequency, and duration clearly.

3. Necessary Lab Tests:
- [List tests needed for further diagnosis or confirmation.]

4. Medical Advice:
- [Lifestyle, dietary, or general clinical advice.]

5. Recommended Specialist:
- [Only the specialty name, e.g., Cardiologist, ENT, General Physician.]

6. Warning Signs requiring urgent attention:
- [List any signs the patient must watch for.]

7. Suggested Diet Chart (basic healthy weekly plan)

---

If there is no recommendation in any section, write **None**. Always number all sections clearly from 0 to 6. Follow the structure exactly.
"""


    response = client.chat.completions.create(
        model="anthropic/claude-sonnet-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800,
        extra_headers={
            "HTTP-Referer": "https://prescription.aiha.live",
            "X-Title": "PrescriptionApp"
        }
    )

    content = response.choices[0].message.content

    # Use flexible regex patterns to extract each section
    summary = extract_section(content, r"(?:[#*\s]*?)0\.\s*Summary of Findings:?\s*(.*?)(?=\n[#*\s]*?1\.)", "No summary available")
    diagnosis = extract_section(content, r"1\.\s*\**Diagnosis\**:?(.*?)(?:2\.|\Z)", "N/A")
    medicines_text = extract_section(content, r"2\.\s*\**Recommended Medicines\**:?(.*?)(?:3\.|\Z)", "None")
    tests = extract_section(content, r"3\.\s*\**Necessary Lab Tests\**:?(.*?)(?:4\.|\Z)", "None")
    advice = extract_section(content, r"4\.\s*\**Medical Advice\**:?(.*?)(?:5\.|\Z)", "Follow general guidelines")
    specialty_raw = extract_section(content, r"5\.\s*\**Recommended Specialist\**:?(.*?)(?:6\.|\Z)", "General Physician")
    warning_signs = extract_section(content, r"6\.\s*\**Warning Signs.*?\**:?(.*)", "None specified")
    recommended_specialty = extract_recommended_specialty_from_raw(content)
   # diet_chart =  extract_section(content, r"7\.\s*Suggested Diet Chart\s*:?([\s\S]*)", "None").strip()
    diet_chart = extract_section(content, r"7\.\s*\**Suggested Diet Chart.*?\**:?(.*)", "None specified")

    return {
	"summary": summary.strip(),
        "diagnosis": diagnosis.strip(),
        "medicines": parse_medicines(medicines_text),
        "tests": tests.strip(),
        "advice": advice.strip(),
	    #"recommended_specialty": recommended_specialty,
        "recommended_specialty": specialty_raw.strip(),
        "warning_signs": warning_signs.strip(),
        "raw_content": content,
        #'diet_chart':diet_chart,
        "diet_chart": diet_chart.strip(),
    }







def get_ai_prescription_with_image(
    symptoms, duration, gender,
    medical_history=None, allergies=None, age=None,
    current_medications=None, vital_signs=None,
    body_weight=None, body_weight_unit=None,
    body_height=None, body_height_unit=None,
    location=None,
    image_payloads=None
):
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

    prompt_text = f"""
You are an expert medical doctor.
Please analyze the patient's clinical information and the lab test image (if provided), then generate a structured clinical prescription.

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

If an image is provided, interpret it and integrate the findings.

🧠 Your structured clinical response should follow **exactly this format**:

---

0. Summary of Findings  
- [2–3 line clinical overview: include significant symptoms, vitals, and red flags.]
1. Diagnosis  
- [Insert specific diagnosis or differential diagnosis.]
2. Recommended Medicines:
List each medicine **in the following exact structure**, one per line:
- Name: Paracetamol  
  Dosage: 500mg  
  Frequency: 1-1-1 (three times daily)  
  Duration: 5 days

- Name: Omeprazole  
  Dosage: 20mg  
  Frequency: 1-0-0 (once daily before food)  
  Duration: 7 days

3. Necessary Lab Tests  
- [List tests needed for further diagnosis or confirmation.]
4. Medical Advice  
5. Recommended Specialist  
- [Only the specialty name, e.g., Cardiologist, ENT, General Physician.]
6. Warning Signs requiring urgent attention  
- [List any signs the patient must watch for.]
7. Lab Image Interpretation (if any image was uploaded)  
8. Suggested Diet Chart (basic healthy weekly plan)

---

If any section is not applicable, write "None". Be clear and professional.
"""

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}]
    
    if image_payloads:
        messages[0]["content"].extend(image_payloads)

    response = client.chat.completions.create(
        model="anthropic/claude-3-sonnet-20240229",  
        messages=messages,
        temperature=0.3,
        max_tokens=1500,
        extra_headers={
            "HTTP-Referer": "https://prescription.aiha.live",
            "X-Title": "PrescriptionApp"
        }
    )


    content = response.choices[0].message.content

    return {
        "raw_content": content,
        "summary": extract_section(content, r"0\.\s*Summary of Findings\s*:?([\s\S]*?)1\.", "Not available").strip(),
        "diagnosis": extract_section(content, r"1\.\s*Diagnosis\s*:?([\s\S]*?)2\.", "N/A").strip(),
        "medicines": parse_medicines(extract_section(content, r"2\.\s*Recommended Medicines\s*:?([\s\S]*?)3\.", "None")),
        "tests": extract_section(content, r"3\.\s*Necessary Lab Tests\s*:?([\s\S]*?)4\.", "None").strip(),
        "advice": extract_section(content, r"4\.\s*Medical Advice\s*:?([\s\S]*?)5\.", "Follow general advice").strip(),
        "recommended_specialty": clean_specialty(extract_section(content, r"5\.\s*Recommended Specialist\s*:?([\s\S]*?)6\.", "General Physician")).strip(),
        "warning_signs": extract_section(content, r"6\.\s*Warning Signs.*?:\s*([\s\S]*?)7\.", "None specified").strip(),
        "lab_image_interpretation": extract_section(content, r"7\.\s*Lab Image Interpretation\s*:?([\s\S]*?)8\.", "None").strip(),
        "diet_chart": extract_section(content, r"8\.\s*Suggested Diet Chart\s*:?([\s\S]*)", "None").strip()
    }





def extract_section(text, pattern, fallback=""):
    try:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else fallback
    except Exception:
        return fallback




def clean_specialty(text):
    if not text:
        return "General Physician"
    line = next((l.strip() for l in text.strip().splitlines() if l.strip()), "")
    line = re.sub(r"^[-•*:\.]+\s*", "", line)
    return line.rstrip(":.").strip() or "General Physician"




def parse_medicines(medicines_text):
    medicines = []
    current_medicine = {}

    for line in medicines_text.strip().splitlines():
        line = line.strip()

        if line.startswith("- Name:"):
            # Start of a new medicine
            if current_medicine:
                medicines.append(current_medicine)
                current_medicine = {}
            current_medicine["name"] = line.replace("- Name:", "").strip()

        elif line.startswith("Dosage:"):
            current_medicine["dosage"] = line.replace("Dosage:", "").strip()

        elif line.startswith("Frequency:"):
            current_medicine["frequency"] = line.replace("Frequency:", "").strip()

        elif line.startswith("Duration:"):
            current_medicine["duration"] = line.replace("Duration:", "").strip()

    if current_medicine:
        medicines.append(current_medicine)

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






def interpret_lab_images_only(image_payloads, gender="Not specified"):
    """
    Send only lab images to AI model and get interpretation.
    """
    prompt_text = f"""
You are an expert medical doctor.

Please analyze the uploaded lab test image(s) and provide a clear, concise interpretation of what the image(s) suggest medically.

- Patient Gender: {gender}

Respond with only the interpretation. No diagnosis, no prescription, no formatting. Avoid any sections or headings.
If nothing is visible or conclusive, say so.
"""

    messages = [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}]

    if image_payloads:
        messages[0]["content"].extend(image_payloads)

    response = client.chat.completions.create(
        model="anthropic/claude-3-sonnet-20240229",
        messages=messages,
        temperature=0.2,
        max_tokens=600,
        extra_headers={
            "HTTP-Referer": "https://prescription.aiha.live",
            "X-Title": "LabTestInterpretation"
        }
    )

    return response.choices[0].message.content.strip()











