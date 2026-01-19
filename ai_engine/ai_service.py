
from openai import OpenAI
import os
import json
from django.conf import settings
import random
import re
import math
import time

def get_client():
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        print("WARNING: OPENROUTER_API_KEY not found.")
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

def extract_json_substring(text):
    """
    Extracts the first valid JSON object or array from the text using stack-based matching.
    """
    text = text.strip()
    stack = []
    start_index = -1
    
    # Locate the first opening brace/bracket
    for i, char in enumerate(text):
        if char in '{[':
            start_index = i
            stack.append(char)
            break
            
    if start_index == -1:
        return None

    # Continue from there
    for i in range(start_index + 1, len(text)):
        char = text[i]
        if char in '{[':
            stack.append(char)
        elif char in '}]':
            if not stack:
                continue # imbalance or previous closure?
            
            last = stack[-1]
            if (char == '}' and last == '{') or (char == ']' and last == '['):
                stack.pop()
                if not stack:
                    # Found the matching closer for the top-level element
                    return text[start_index : i+1]
            else:
                # Mismatched nesting (e.g. { ] ) - invalid JSON structure
                return None
                
    return None

def generate_json_with_retry(client, prompt, retries=3):
    """Generates content and parses JSON with retries using OpenRouter."""
    if not client:
        return None
        
    model_name = getattr(settings, 'OPENROUTER_MODEL', "google/gemini-2.0-flash-exp:free")

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            
            # 1. Cleaner: Remove markdown code blocks
            content_clean = content.replace('```json', '').replace('```', '').strip()
            
            # 2. Try Standard Decoding first (fastest)
            try:
                # strict=False allows control characters
                obj, _ = json.JSONDecoder(strict=False).raw_decode(content_clean)
                return obj
            except json.JSONDecodeError:
                pass
            
            # 3. Smart Extraction (Stack based)
            extracted_json = extract_json_substring(content_clean)
            if extracted_json:
                try:
                    return json.loads(extracted_json, strict=False)
                except json.JSONDecodeError:
                    pass
            
            # 4. Fallback: Naive slicing (if stack failed due to malformed chars)
            if '{' in content_clean:
                try:
                    start = content_clean.find('{')
                    end = content_clean.rfind('}') + 1
                    # Try cleaning trailing commas which is a common AI error
                    clean_slice = re.sub(r',(\s*[}\]])', r'\1', content_clean[start:end])
                    return json.loads(clean_slice, strict=False)
                except:
                    pass
            if '[' in content_clean:
                try:
                    start = content_clean.find('[')
                    end = content_clean.rfind(']') + 1
                    clean_slice = re.sub(r',(\s*[}\]])', r'\1', content_clean[start:end])
                    return json.loads(clean_slice, strict=False)
                except:
                    pass

            print(f"WARNING: No valid JSON found in attempt {attempt+1}. Content snippet: {content_clean[:200]}...")
            
        except Exception as e:
            print(f"Error in attempt {attempt+1}: {e}")
            
    return None

def generate_question(topic_name, difficulty):
    client = get_client()
    if not client:
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

    return generate_json_with_retry(client, prompt)

def explain_answer(question_text, user_answer, correct_answer):
    client = get_client()
    if not client:
        return "AI explanation unavailable (API Key missing)."

    model_name = getattr(settings, 'OPENROUTER_MODEL', "google/gemini-2.0-flash-exp:free")

    prompt = f"""
    Question: {question_text}
    User Answer: {user_answer}
    Correct Answer: {correct_answer}
    
    Explain why the correct answer is correct and, if the user was wrong, why their answer is incorrect.
    Keep it concise and helpful for a student.
    """
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating explanation: {e}"

def generate_test_questions(subject_name, num_questions, difficulty='Medium'):
    print(f"DEBUG: generate_test_questions called for {subject_name}, {num_questions}")
    client = get_client()
    if not client:
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
            'Reading Comprehension': 15,
            'Cloze Test': 5,
            'Error Detection': 5,
            'Sentence Rearrangement (Para Jumbles)': 5,
            'Fill in the Blanks': 5,
            'Word Swap': 3,
            'Phrase Replacement': 2
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

    BATCH_SIZE = 5 # Reduced from 20 to prevent JSON truncation/parsing errors
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
                    time.sleep(4) # Rate limit protection
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
                    6. VERIFY YOUR ANSWERS: Ensure option A-E are distinct and the 'correct_option' is logically derivable from the data.
                    7. EXPLANATION: Provide a step-by-step calculation or reasoning for the correct option.
                    
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
                                "explanation": "Step 1: ... Step 2: ... Final Answer: ...",
                                "topic": "{topic}"
                            }},
                            ... ({questions_in_set} questions)
                        ]
                    }}
                    """

                    data_set = generate_json_with_retry(client, prompt)
                    
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
                5. ACCURACY CHECK: Double-check the calculation/reasoning. The 'correct_option' MUST be correct.
                6. OUTPUT FORMAT: Raw JSON only. NO markdown blocks (```json). NO intro/outro text.
                
                Provide the output as a JSON array of objects, where each object has:
                - text: The question text
                - option_a: Option A
                - option_b: Option B
                - option_c: Option C
                - option_d: Option D
                - option_e: Option E
                - correct_option: The correct option letter (A, B, C, D, or E)
                - explanation: A detailed step-by-step explanation proving the correct option.
                - topic: The specific sub-topic name (use '{topic}')
                """
                
                topic_questions = generate_json_with_retry(client, prompt)
                
                if topic_questions and isinstance(topic_questions, list):
                    all_questions.extend(topic_questions)
                else:
                    print(f"FAILED to generate questions for {topic} after retries.")
                    
    else:
        # Fallback to batch generation
        num_batches = math.ceil(num_questions / BATCH_SIZE)
        
        for i in range(num_batches):
            time.sleep(4) # Rate limit protection
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
            5. OUTPUT FORMAT: Raw JSON only. NO markdown blocks (```json). NO intro/outro text.
            
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

            batch_questions = generate_json_with_retry(client, prompt)
            
            if batch_questions and isinstance(batch_questions, list):
                all_questions.extend(batch_questions)
            else:
                print(f"FAILED to generate batch {i+1} after retries.")
            
    return all_questions

def generate_topic_questions(topic_name, num_questions, difficulty='Medium'):
    client = get_client()
    if not client:
        return []

    prompt = f"""
    Act as an expert exam setter for banking exams.
    Generate {num_questions} UNIQUE and HIGH-QUALITY multiple-choice questions specifically on the topic '{topic_name}'.
    
    CRITICAL INSTRUCTIONS:
    1. Topic: {topic_name}
    2. Difficulty Level: {difficulty}.
    3. Questions must be modeled after actual previous year question papers.
    4. Ensure NO repetition of question patterns.
    5. OUTPUT FORMAT: Raw JSON only. NO markdown blocks (```json). NO intro/outro text.
    
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

    return generate_json_with_retry(client, prompt) or []