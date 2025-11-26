import os
import django
from django.conf import settings
import google.generativeai as genai
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

genai.configure(api_key=settings.GEMINI_API_KEY)

def test_generation():
    model_name = 'gemini-3-pro-preview'
    print(f"Testing model: {model_name}")
    
    try:
        model = genai.GenerativeModel(model_name)
        prompt = "Explain the concept of compound interest in one sentence."
        print("Sending prompt...")
        
        response = model.generate_content(prompt)
        print(f"Response received: {response.text}")
        print("SUCCESS: Model is working.")
        
    except Exception as e:
        print(f"FAILURE: Error generating content: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
