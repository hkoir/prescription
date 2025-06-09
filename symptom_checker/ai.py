import os
from openai import OpenAI
import json



# utils/translation_utils.py

from deep_translator import GoogleTranslator
from django.utils.translation import get_language

def translate_from_english(text):
    target_lang = get_language()
    if target_lang == 'en' or not text:
        return text
    try:
        return GoogleTranslator(source='en', target=target_lang).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def translate_to_english(text):
    source_lang = get_language()
    if source_lang == 'en' or not text:
        return text
    try:
        return GoogleTranslator(source=source_lang, target='en').translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)




def get_next_symptom_question(previous_qa):
    if not previous_qa:
        return "Question: What symptoms are you currently experiencing?"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional medical AI assistant. "
                "Your task is to ask ONE medically relevant follow-up question at a time. "
                "DO NOT ask multiple questions. DO NOT include greetings, explanations, or context. "
                "Avoid all conversational phrases like 'I see', 'Okay', 'Thanks', or introductions. "
                 "Only output ONE SHORT, PRECISE medical question, starting with 'Question:'. "
                "Limit the length of the question to a single sentence and do not exceed 20 words.\n\n"
                "✅ Good: Question: Have you experienced a fever recently?\n"
                "❌ Bad: Question: Have you experienced fever or chills, body ache, and vomiting recently?\n"
                "❌ Bad: Thanks for answering! Can you tell me more about your cough and whether you've had fever?\n"
                            
            )
        },

        
        {
            "role": "assistant",
            "content": "Question: What symptoms are you currently experiencing?"
        },
    ]

    for item in previous_qa:
        messages.append({"role": "user", "content": item["question"]})
        messages.append({"role": "assistant", "content": item["answer"]})

    messages.append({"role": "user", "content": "Ask the next follow-up medical question."})

    response = client.chat.completions.create(
        model="openai/gpt-4-turbo",  # or any model from the table above
        messages=messages,
        temperature=0.3,
    )


    # Extract only the question line if present
    response_text = response.choices[0].message.content.strip()
    if "Question:" in response_text:
        return response_text.split("Question:", 1)[-1].strip().rstrip(".") + "?"
    return "Question: " + response_text.strip().rstrip(".") + "?"





def get_final_symptom_summary(previous_qa, age=None, gender=None, weight=None, height=None, location=None, duration=None):
    if all([age, gender, weight, height, location, duration]):
        patient_info = (
            f"Patient is a {age}-year-old {gender}, weighs {weight} kg, height {height} cm, "
            f"has been experiencing symptoms for {duration} days, and is located in {location}."
        )
    else:
        patient_info = "Patient details are not fully provided."

    if not previous_qa or not any(item.get("question") and item.get("answer") for item in previous_qa):
        return {
            "probable_disease": None,
            "probable_symptoms": None,
            "ai_summary": "No valid symptom information provided to summarize."
        }

    messages = [
        {
           "role": "system",
            "content": (
                f"You are a professional and cautious medical AI assistant. {patient_info} "
                "You must analyze the symptom dialogue to determine:\n"
                "1. The most likely diagnosis (disease name).\n"
                "2. A list of typical symptoms for that diagnosis.\n"
                "3. A clear summary with general advice.\n\n"
                "**DO NOT invent diseases or symptoms.**\n"
                "**Base your reasoning only on clinical evidence and common presentations.**\n"
                "**Be conservative — if data is insufficient, say so.**\n\n"
               "Respond in this exact JSON format only:\n"
                "{\n"
                '  "probable_disease": "Disease name here",\n'
                '  "probable_symptoms": "Comma-separated list of typical symptoms",\n'
                '  "ai_summary": "Short paragraph summarizing findings and suggestions",\n'
                '  "is_confident": true or false\n'
                "}"

            )

        }
    ]

    for item in previous_qa:
        question = item.get("question", "").strip()
        answer = item.get("answer", "").strip()
        translated_answer = translate_to_english(answer)

        if question and translated_answer:
            messages.append({"role": "assistant", "content": question})  # AI previously asked
            messages.append({"role": "user", "content": translated_answer})  # user replied

    messages.append({"role": "user", "content": "Please return the result in JSON format as instructed."})

     
    response = client.chat.completions.create(
        model="openai/gpt-4-turbo", 
        messages=messages,
        temperature=0.5,
    )


    try:
        result = json.loads(response.choices[0].message.content.strip())
    except Exception:
        result = {
            "probable_disease": None,
            "probable_symptoms": None,
            "ai_summary": response.choices[0].message.content.strip(),
            "is_confident": False
        }

    return result
