import google.generativeai as genai
import os
import json
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_model():
    return genai.GenerativeModel('gemini-2.0-flash')

def generate_question(topic_name, difficulty):
    model = get_model()
    if not model:
        return None

    prompt = f"""
    Generate a multiple-choice question for a banking exam (like SBI PO) on the topic '{topic_name}'.
    Difficulty: {difficulty}.
    Provide the output in JSON format with the following keys:
    - text: The question text
    - option_a: Option A
    - option_b: Option B
    - option_c: Option C
    - option_d: Option D
    - option_e: Option E
    - correct_option: The correct option letter (A, B, C, D, or E)
    - explanation: A detailed explanation of the solution
    """

    try:
        response = model.generate_content(prompt)
        print(f"Raw AI Response: {response.text}") # Debugging
        # Clean up response to ensure it's valid JSON
        content = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(content)
    except Exception as e:
        print(f"Error generating question: {e}")
        import traceback
        traceback.print_exc()
        
        # Debug: List available models
        try:
            print("Available models:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(m.name)
        except Exception as list_err:
            print(f"Error listing models: {list_err}")
            
        return None

def explain_answer(question_text, user_answer, correct_answer):
    model = get_model()
    if not model:
        return "AI explanation unavailable (API Key missing)."

    prompt = f"""
    Question: {question_text}
    User Answer: {user_answer}
    Correct Answer: {correct_answer}
    
    Explain why the correct answer is correct and, if the user was wrong, why their answer is incorrect.
    Keep it concise and helpful for a student.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating explanation: {e}"
import random

def generate_test_questions(subject_name, num_questions, difficulty='Medium'):
    model = get_model()
    if not model:
        return []

    # Define sub-topics for variety
    sub_topics_map = {
        'Quantitative Aptitude': [
            'Data Interpretation (Table/Bar/Line)', 'Number Series (Missing/Wrong)', 
            'Quadratic Equations', 'Simplification & Approximation', 
            'Arithmetic (Profit Loss, SI/CI, Time Work)', 'Mensuration', 'Probability'
        ],
        'Reasoning Ability': [
            'Puzzles (Floor/Box/Day)', 'Seating Arrangement (Circular/Linear)', 
            'Syllogism', 'Inequality', 'Coding-Decoding', 'Blood Relations', 
            'Direction Sense', 'Input-Output'
        ],
        'English Language': [
            'Reading Comprehension', 'Cloze Test', 'Error Detection', 
            'Sentence Rearrangement (Para Jumbles)', 'Fill in the Blanks', 
            'Word Swap', 'Phrase Replacement'
        ]
    }

    # Batch generation to avoid timeouts and JSON errors
    BATCH_SIZE = 5
    all_questions = []
    
    import math
    num_batches = math.ceil(num_questions / BATCH_SIZE)
    
    for i in range(num_batches):
        current_batch_size = min(BATCH_SIZE, num_questions - len(all_questions))
        
        # Select random sub-topics to focus on for this batch
        available_topics = sub_topics_map.get(subject_name, ['General'])
        selected_topics = random.sample(available_topics, min(len(available_topics), 3))
        topics_str = ", ".join(selected_topics)

        prompt = f"""
        Act as an expert exam setter for SBI PO and IBPS PO exams.
        Generate {current_batch_size} UNIQUE and HIGH-QUALITY multiple-choice questions for '{subject_name}'.
        
        CRITICAL INSTRUCTIONS:
        1. Focus specifically on these topics: {topics_str}.
        2. Difficulty Level: {difficulty}.
        3. Questions must be modeled after actual previous year question papers (2020-2024).
        4. Ensure NO repetition of question patterns.
        5. For 'Quantitative Aptitude', include realistic data values.
        6. For 'Reasoning', ensure puzzles are logically sound.
        
        Provide the output as a JSON array of objects, where each object has:
        - text: The question text (include directions if needed)
        - option_a: Option A
        - option_b: Option B
        - option_c: Option C
        - option_d: Option D
        - option_e: Option E
        - correct_option: The correct option letter (A, B, C, D, or E)
        - explanation: A detailed step-by-step explanation
        - topic: The specific sub-topic name
        """

        try:
            response = model.generate_content(prompt)
            print(f"Raw AI Response (Batch {i+1}): {response.text[:100]}...") # Debugging
            content = response.text.replace('```json', '').replace('```', '').strip()
            
            # Sometimes the model might return text before or after the JSON
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx]
                
            batch_questions = json.loads(content)
            all_questions.extend(batch_questions)
            
        except Exception as e:
            print(f"Error generating batch {i+1}: {e}")
            import traceback
            traceback.print_exc()
            # Continue to next batch even if one fails
            continue
            
    return all_questions

def generate_topic_questions(topic_name, num_questions, difficulty='Medium'):
    model = get_model()
    if not model:
        return []

    prompt = f"""
    Act as an expert exam setter for banking exams.
    Generate {num_questions} UNIQUE and HIGH-QUALITY multiple-choice questions specifically on the topic '{topic_name}'.
    
    CRITICAL INSTRUCTIONS:
    1. Topic: {topic_name}
    2. Difficulty Level: {difficulty}.
    3. Questions must be modeled after actual previous year question papers.
    4. Ensure NO repetition of question patterns.
    
    Provide the output as a JSON array of objects, where each object has:
    - text: The question text (include directions if needed)
    - option_a: Option A
    - option_b: Option B
    - option_c: Option C
    - option_d: Option D
    - option_e: Option E
    - correct_option: The correct option letter (A, B, C, D, or E)
    - explanation: A detailed step-by-step explanation
    """

    try:
        response = model.generate_content(prompt)
        content = response.text.replace('```json', '').replace('```', '').strip()
        
        start_idx = content.find('[')
        end_idx = content.rfind(']') + 1
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx]
            
        return json.loads(content)
    except Exception as e:
        print(f"Error generating topic questions: {e}")
        return []
