import google.generativeai as genai
import os
import json
from django.conf import settings
import random
import math

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_model():
    # User requested Pro model. 3.0 has quota issues, 1.5 is 404. Using 2.0 Pro Exp.
    return genai.GenerativeModel('gemini-2.0-flash')

def generate_question(topic_name, difficulty):
    model = get_model()
    if not model:
        return None

    prompt = f"""
    Generate a multiple-choice question for a banking exam (like RRB Clerk) on the topic '{topic_name}'.
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

def generate_test_questions(subject_name, num_questions, difficulty='Medium'):
    print(f"DEBUG: generate_test_questions called for {subject_name}, {num_questions}")
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
    
    # Topic-wise question distribution for RRB Clerk (40 questions per subject)
    TOPIC_DISTRIBUTION = {
        'Quantitative Aptitude': {
            'Data Interpretation (Table/Bar/Line)': 10,
            'Number Series (Missing/Wrong)': 5,
            'Simplification & Approximation': 10,
            'Arithmetic (Profit Loss, SI/CI, Time Work)': 10,
            'Quadratic Equations': 3,
            'Mensuration': 1,
            'Probability': 1
        },
        'Reasoning Ability': {
            'Puzzles (Floor/Box/Day)': 10,
            'Seating Arrangement (Circular/Linear)': 10,
            'Syllogism': 5,
            'Inequality': 5,
            'Coding-Decoding': 3,
            'Blood Relations': 3,
            'Direction Sense': 2,
            'Input-Output': 2
        },
        'English Language': {
            'Reading Comprehension': 10,
            'Cloze Test': 5,
            'Error Detection': 5,
            'Sentence Rearrangement (Para Jumbles)': 5,
            'Fill in the Blanks': 3,
            'Word Swap': 1,
            'Phrase Replacement': 1
        }
    }

    BATCH_SIZE = 5
    all_questions = []
    
    # Check if we have a specific distribution for this subject
    if subject_name in TOPIC_DISTRIBUTION and num_questions == sum(TOPIC_DISTRIBUTION[subject_name].values()):
        # Use the predefined distribution
        topic_distribution = TOPIC_DISTRIBUTION[subject_name]
        
        for topic, count in topic_distribution.items():
            if count == 0:
                continue
                
            prompt = f"""
            Act as an expert exam setter for RRB Clerk exams.
            Generate {count} UNIQUE and HIGH-QUALITY multiple-choice questions for '{subject_name}' specifically on the topic '{topic}'.
            
            CRITICAL INSTRUCTIONS:
            1. Topic: {topic}
            2. Difficulty Level: {difficulty}.
            3. Questions must be modeled after actual previous year question papers.
            4. Ensure NO repetition of question patterns.
            
            SPECIAL INSTRUCTION FOR DATA INTERPRETATION:
            If the topic involves a graph, chart, or TABLE (Line Graph, Bar Chart, Pie Chart, Table), you MUST provide structured data for rendering it.
            DO NOT describe the data in the 'text' field (e.g., do not say "Imagine a table...").
            Instead, put the data details ONLY in the 'chart_data' field.
            
            Provide the output as a JSON array of objects, where each object has:
            - text: The question text (include directions if needed, but NO chart/table description)
            - option_a: Option A
            - option_b: Option B
            - option_c: Option C
            - option_d: Option D
            - option_e: Option E
            - correct_option: The correct option letter (A, B, C, D, or E)
            - explanation: A detailed step-by-step explanation
            - topic: The specific sub-topic name (use '{topic}')
            - chart_data: (OPTIONAL, ONLY for graphs/charts/tables) A JSON object with:
                - type: "bar", "line", "pie", or "table"
                - title: Title of the chart or table
                
                # IF TYPE IS "bar", "line", or "pie":
                - labels: Array of X-axis labels (e.g., ["Jan", "Feb", "Mar"])
                - datasets: Array of objects, each with:
                    - label: Dataset label (e.g., "Sales")
                    - data: Array of numbers corresponding to labels
                    
                # IF TYPE IS "table":
                - headers: Array of column headers (e.g., ["Year", "Sales", "Profit"])
                - rows: Array of arrays, where each inner array is a row of data (e.g., [["2020", "100", "20"], ["2021", "150", "30"]])
            
            EXAMPLE JSON OBJECT:
            {{
                "text": "What is the difference between sales in Jan and Feb?",
                "option_a": "10",
                "option_b": "20",
                "option_c": "30",
                "option_d": "40",
                "option_e": "50",
                "correct_option": "A",
                "explanation": "Jan: 100, Feb: 110. Diff = 10.",
                "topic": "Data Interpretation",
                "chart_data": {{
                    "type": "bar",
                    "title": "Monthly Sales",
                    "labels": ["Jan", "Feb", "Mar"],
                    "datasets": [{{"label": "Sales", "data": [100, 110, 120]}}]
                }}
            }}
            """
            
            try:
                response = model.generate_content(prompt)
                print(f"Raw AI Response for {topic} ({count} questions): {response.text[:100]}...")
                content = response.text.replace('```json', '').replace('```', '').strip()
                
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx]
                    topic_questions = json.loads(content)
                    all_questions.extend(topic_questions)
                else:
                    print(f"No JSON array found in response for {topic}. Raw content: {content[:100]}...")
                
            except Exception as e:
                print(f"Error generating questions for topic {topic}: {e}")
                import traceback
                traceback.print_exc()
                continue
    else:
        # Fallback to batch generation
        num_batches = math.ceil(num_questions / BATCH_SIZE)
        
        for i in range(num_batches):
            current_batch_size = min(BATCH_SIZE, num_questions - len(all_questions))
            
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
                print(f"Raw AI Response (Batch {i+1}): {response.text[:100]}...")
                content = response.text.replace('```json', '').replace('```', '').strip()
                
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    content = content[start_idx:end_idx]
                    batch_questions = json.loads(content)
                    all_questions.extend(batch_questions)
                else:
                    print(f"No JSON array found in response for batch {i+1}. Raw content: {content[:100]}...")
                
            except Exception as e:
                print(f"Error generating batch {i+1}: {e}")
                import traceback
                traceback.print_exc()
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
        else:
            return []
            
    except Exception as e:
        print(f"Error generating topic questions: {e}")
        return []