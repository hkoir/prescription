
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

Please analyze the following patient data and provide a structured clinical response in the exact format described.

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

⚠️ Do not combine fields in a single line. Use separate fields: `Name`, `Dosage`, `Frequency`, and `Duration`.

3. Necessary Lab Tests:
- [List tests needed for further diagnosis or confirmation.]

4. Medical Advice:
- [Lifestyle, dietary, or general clinical advice.]

5. Recommended Specialist:
- [Only the specialty name, e.g., Cardiologist, ENT, General Physician.]

6. Warning Signs requiring urgent attention:
- [List any signs the patient must watch for.]

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


    return {
	"summary": summary.strip(),
        "diagnosis": diagnosis.strip(),
        "medicines": parse_medicines(medicines_text),
        "tests": tests.strip(),
        "advice": advice.strip(),
	#"recommended_specialty": recommended_specialty,
        "recommended_specialty": specialty_raw.strip(),
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


