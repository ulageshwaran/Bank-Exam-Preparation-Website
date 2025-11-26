import os
import django
from django.conf import settings
import google.generativeai as genai

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

genai.configure(api_key=settings.GEMINI_API_KEY)

print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
