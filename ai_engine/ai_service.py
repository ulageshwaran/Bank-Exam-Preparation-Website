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

def generate_json_with_retry(model, prompt, retries=3):
    """Generates content and parses JSON with retries."""
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            content = response.text.replace('```json', '').replace('```', '').strip()
            
            # Try to find the first JSON object or array
            start_idx = -1
            if '{' in content:
                start_idx = content.find('{')
            if '[' in content:
                idx = content.find('[')
                if start_idx == -1 or (idx != -1 and idx < start_idx):
                    start_idx = idx
            
            if start_idx != -1:
                content = content[start_idx:]
                try:
                    # strict=False allows control characters like newlines in strings
                    obj, _ = json.JSONDecoder(strict=False).raw_decode(content)
                    return obj
                except json.JSONDecodeError:
                    # Fallback to simple slicing if raw_decode fails (e.g. incomplete JSON)
                    pass

            # Fallback: Try manual slicing if raw_decode failed
            if content.startswith('{') or content.find('{') != -1:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    return json.loads(content[start_idx:end_idx], strict=False)
            
            if content.startswith('[') or content.find('[') != -1:
                start_idx = content.find('[')
                end_idx = content.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    return json.loads(content[start_idx:end_idx], strict=False)
            
            print(f"WARNING: No valid JSON found in attempt {attempt+1}")
            
        except Exception as e:
            print(f"Error in attempt {attempt+1}: {e}")
            import traceback
            traceback.print_exc()
            
    return None

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

    return generate_json_with_retry(model, prompt)

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
        ],
        'Computer Knowledge': [
            'Computer Hardware', 'Software & Operating Systems', 'Internet & Networking',
            'DBMS', 'MS Office (Word, Excel, PowerPoint)', 'Computer Security',
            'Computer Abbreviations', 'History & Generations'
        ],
        'General Awareness': [
            'Current Affairs (National/International)', 'Banking & Financial Awareness',
            'Static GK (Parks, Dams, Capitals)', 'Sports', 'Awards & Honours',
            'Books & Authors', 'Important Days'
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
        },
        'Computer Knowledge': {
            'MS Office (Word, Excel, PowerPoint)': 10,
            'Internet & Networking': 8,
            'Computer Hardware': 5,
            'Software & Operating Systems': 5,
            'Computer Security': 4,
            'DBMS': 4,
            'Computer Abbreviations': 2,
            'History & Generations': 2
        },
        'General Awareness': {
            'Current Affairs (National/International)': 15,
            'Banking & Financial Awareness': 10,
            'Static GK (Parks, Dams, Capitals)': 5,
            'Sports': 3,
            'Awards & Honours': 3,
            'Books & Authors': 2,
            'Important Days': 2
        }
    }

    BATCH_SIZE = 5
    all_questions = []
    
    # Check if we have a specific distribution for this subject
    if subject_name in TOPIC_DISTRIBUTION and num_questions == sum(TOPIC_DISTRIBUTION[subject_name].values()):
        # Use the predefined distribution
        topic_distribution = TOPIC_DISTRIBUTION[subject_name]
        
        # Topics that require grouped questions (Sets of 5)
        GROUPED_TOPICS = [
            'Data Interpretation (Table/Bar/Line)',
            'Reading Comprehension',
            'Puzzles (Floor/Box/Day)',
            'Seating Arrangement (Circular/Linear)'
        ]

        for topic, count in topic_distribution.items():
            if count == 0:
                continue
            
            # Check if this is a grouped topic
            if topic in GROUPED_TOPICS:
                # Generate in sets of 5
                num_sets = math.ceil(count / 5)
                
                for set_idx in range(num_sets):
                    questions_in_set = min(5, count - (set_idx * 5))
                    if questions_in_set <= 0: break

                    # Determine chart type for Data Interpretation
                    di_instruction = ""
                    chart_json_template = '"chart_data": null'
                    
                    if topic == 'Data Interpretation (Table/Bar/Line)':
                        chart_type = random.choice(['table', 'bar', 'line', 'pie'])
                        di_instruction = f"""
                        SPECIAL INSTRUCTION FOR DATA INTERPRETATION:
                        - Create a {chart_type.upper()} CHART.
                        - Provide structured data in 'common_data' -> 'chart_data'.
                        - DO NOT describe the data in the question text.
                        """
                        
                        if chart_type == 'table':
                            di_instruction += "- FOR TABLES: You MUST provide 'headers' (list of strings) and 'rows' (list of lists of strings)."
                            chart_json_template = """
                            "chart_data": {
                                "type": "table", 
                                "title": "Table Title",
                                "headers": ["Col1", "Col2"],
                                "rows": [["Row1Data1", "Row1Data2"], ["Row2Data1", "Row2Data2"]] 
                            }
                            """
                        else:
                            di_instruction += "- FOR GRAPHS: You MUST provide 'labels' (list of strings) and 'datasets' (list of objects with 'label' and 'data')."
                            chart_json_template = f"""
                            "chart_data": {{
                                "type": "{chart_type}", 
                                "title": "{chart_type.capitalize()} Chart Title",
                                "labels": ["Label1", "Label2", "Label3"],
                                "datasets": [
                                    {{
                                        "label": "Series 1",
                                        "data": [10, 20, 30]
                                    }}
                                ]
                            }}
                            """

                    prompt = f"""
                    Act as an expert exam setter for RRB Clerk exams.
                    Generate a SET of {questions_in_set} multiple-choice questions for '{subject_name}' on the topic '{topic}'.
                    
                    CRITICAL INSTRUCTIONS:
                    1. Topic: {topic}
                    2. Difficulty Level: {difficulty}.
                    3. This must be a LINKED SET of questions based on a common Data Block (Graph, Table, Passage, or Puzzle).
                    4. First, generate the Common Data Block.
                    5. Then, generate {questions_in_set} questions based on that SAME Data Block.
                    
                    {di_instruction}
                    
                    SPECIAL INSTRUCTION FOR PUZZLES/SEATING ARRANGEMENT:
                    - Provide the main puzzle text/conditions in 'common_data' -> 'text'.
                    
                    SPECIAL INSTRUCTION FOR READING COMPREHENSION:
                    - Provide the passage in 'common_data' -> 'text'.

                    Provide the output as a SINGLE JSON OBJECT with this structure:
                    {{
                        "common_data": {{
                            "text": "Passage or Puzzle text here (if applicable)",
                            {chart_json_template}
                        }},
                        "questions": [
                            {{
                                "text": "Question text...",
                                "option_a": "...",
                                "option_b": "...",
                                "option_c": "...",
                                "option_d": "...",
                                "option_e": "...",
                                "correct_option": "A",
                                "explanation": "...",
                                "topic": "{topic}"
                            }},
                            ... ({questions_in_set} questions)
                        ]
                    }}
                    """

                    data_set = generate_json_with_retry(model, prompt)
                    
                    if data_set and isinstance(data_set, dict):
                        common_data = data_set.get('common_data', {})
                        questions = data_set.get('questions', [])
                        
                        # Validate Table Data
                        if 'chart_data' in common_data and common_data['chart_data']:
                            cd = common_data['chart_data']
                            if cd.get('type') == 'table':
                                if 'rows' not in cd or not isinstance(cd['rows'], list) or len(cd['rows']) == 0:
                                    print(f"WARNING: Table data missing 'rows' for {topic}. Attempting to fix or skip.")
                                    if 'rows' not in cd: cd['rows'] = []
                        
                        # Flatten: Inject common data into each question
                        for q in questions:
                            if 'chart_data' in common_data:
                                q['chart_data'] = common_data['chart_data']
                            if 'text' in common_data and common_data['text']:
                                q['passage'] = common_data['text']
                                
                            all_questions.append(q)
                    else:
                        print(f"FAILED to generate grouped questions for {topic} Set {set_idx+1} after retries.")

            else:
                # Standard independent questions generation
                prompt = f"""
                Act as an expert exam setter for RRB Clerk exams.
                Generate {count} UNIQUE and HIGH-QUALITY multiple-choice questions for '{subject_name}' specifically on the topic '{topic}'.
                
                CRITICAL INSTRUCTIONS:
                1. Topic: {topic}
                2. Difficulty Level: {difficulty}.
                3. Questions must be modeled after actual previous year question papers.
                4. Ensure NO repetition of question patterns.
                
                Provide the output as a JSON array of objects, where each object has:
                - text: The question text
                - option_a: Option A
                - option_b: Option B
                - option_c: Option C
                - option_d: Option D
                - option_e: Option E
                - correct_option: The correct option letter (A, B, C, D, or E)
                - explanation: A detailed step-by-step explanation
                - topic: The specific sub-topic name (use '{topic}')
                """
                
                topic_questions = generate_json_with_retry(model, prompt)
                
                if topic_questions and isinstance(topic_questions, list):
                    all_questions.extend(topic_questions)
                else:
                    print(f"FAILED to generate questions for {topic} after retries.")
                    
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

            batch_questions = generate_json_with_retry(model, prompt)
            
            if batch_questions and isinstance(batch_questions, list):
                all_questions.extend(batch_questions)
            else:
                print(f"FAILED to generate batch {i+1} after retries.")
            
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

    return generate_json_with_retry(model, prompt) or []