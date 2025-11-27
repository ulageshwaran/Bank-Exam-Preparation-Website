import os
import django
import sys
import json

# Setup Django environment
sys.path.append(r'c:\Users\ULAGESHWARAN E\python\bank exam')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

from ai_engine.ai_service import generate_test_questions

def test_generation():
    print("Starting test generation...")
    try:
        # Try generating a full batch (40 questions) to trigger topic-wise logic
        questions = generate_test_questions('Quantitative Aptitude', 40, 'Medium')
        print(f"Generated {len(questions)} questions.")
        
        if questions:
            print("First question keys:", questions[0].keys())
            print("First question text:", questions[0].get('text', 'MISSING'))
        else:
            print("No questions returned.")
            
    except Exception as e:
        print(f"Error during generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_generation()
