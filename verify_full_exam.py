import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

from ai_engine.ai_service import generate_test_questions

def verify_full_exam():
    print("Starting Full Exam Verification...")
    
    # 1. Quantitative Aptitude
    print("\n--- Generating Quantitative Aptitude (40 Questions) ---")
    quant_questions = generate_test_questions('Quantitative Aptitude', 40)
    print(f"Quant Questions Generated: {len(quant_questions)}")
    
    # 2. Reasoning Ability
    print("\n--- Generating Reasoning Ability (40 Questions) ---")
    reasoning_questions = generate_test_questions('Reasoning Ability', 40)
    print(f"Reasoning Questions Generated: {len(reasoning_questions)}")
    
    total = len(quant_questions) + len(reasoning_questions)
    print(f"\nTotal Questions: {total}/80")
    
    if len(quant_questions) == 40 and len(reasoning_questions) == 40:
        print("SUCCESS: Full exam generated correctly.")
    else:
        print("FAILURE: Question count mismatch.")
        if len(quant_questions) != 40:
            print(f" - Quant missing {40 - len(quant_questions)} questions")
        if len(reasoning_questions) != 40:
            print(f" - Reasoning missing {40 - len(reasoning_questions)} questions")

if __name__ == "__main__":
    verify_full_exam()
