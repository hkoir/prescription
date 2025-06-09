

from django.core.cache import cache
import hashlib
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

    


def translate_if_needed(text):
    lang = get_language()  

    # Create a cache key using a hash of the text and language
    cache_key = f"translated:{lang}:{hashlib.md5(text.encode()).hexdigest()}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result

    try:
        translated = GoogleTranslator(source='auto', target=lang).translate(text)
        cache.set(cache_key, translated, timeout=60 * 60 * 24)  # Cache for 24 hours
        return translated
    except Exception:
        return text
