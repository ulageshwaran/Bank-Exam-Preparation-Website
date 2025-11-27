from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ai_engine.ai_service import generate_test_questions
from .models import MockTest, TestSection, TestQuestion, UserTestAttempt, UserTestAnswer
from exams.models import Exam, Subject
from practice.models import Question, Topic, QuestionGroup
import threading

# EXAM CONFIGURATIONS - Question distribution for different exam types
EXAM_CONFIGURATIONS = {
    'SBI': {
        'Prelims': {
            'duration': 60,
            'subjects': {
                'English Language': 30,
                'Quantitative Aptitude': 35,
                'Reasoning Ability': 35
            }
        }
    },
    'IBPS': {
        'Prelims': {
            'duration': 60,
            'subjects': {
                'English Language': 30,
                'Quantitative Aptitude': 35,
                'Reasoning Ability': 35
            }
        }
    },
    'RRB': {
        'Prelims': {
            'duration': 45,  # Total duration
            'negative_marks': 0.25,
            'sections': [
                {
                    'name': 'Numerical Ability',
                    'subject': 'Quantitative Aptitude',
                    'questions': 40,
                    'duration': 20  # Section-specific duration in minutes
                },
                {
                    'name': 'Reasoning Ability',
                    'subject': 'Reasoning Ability',
                    'questions': 40,
                    'duration': 25  # Section-specific duration in minutes
                }
            ]
        }
    }
}

@login_required
def test_list(request):
    tests = MockTest.objects.all()
    return render(request, 'tests/test_list.html', {'tests': tests})

@login_required
def generate_test_view(request):
    if request.method == 'POST':
        difficulty = request.POST.get('difficulty', 'Medium')
        exam_type = request.POST.get('exam_type', 'SBI')
        stage = request.POST.get('stage', 'Prelims')
        
        # Create a basic placeholder test immediately
        exam = Exam.objects.first() # Assuming SBI PO
        test = MockTest.objects.create(
            title=f"{exam_type} {stage} Mock Test {MockTest.objects.count() + 1}",
            exam=exam,
            duration=60,  # Default, will be updated based on config
            difficulty=difficulty,
            exam_type=exam_type,
            stage=stage
        )
        
        # Get configuration for the selected exam type and stage
        config = EXAM_CONFIGURATIONS.get(exam_type, {}).get(stage, None)
        
        if config:
            # Use configuration from EXAM_CONFIGURATIONS
            test.duration = config['duration']
            test.save()
            
            # Check if this is a section-based config (RRB) or subject-based config (SBI/IBPS)
            if 'sections' in config:
                # Section-based configuration (RRB)
                total_questions = 0
                section_order = 1
                
                for section_config in config['sections']:
                    sub_name = section_config['subject']
                    count = section_config['questions']
                    section_name = section_config['name']
                    section_duration = section_config['duration']
                    total_questions += count
                    
                    questions_data = generate_test_questions(sub_name, count, difficulty)
                    
                    if questions_data:
                        # Get or create subject
                        subject = Subject.objects.filter(name=sub_name).first()
                        if not subject:
                            continue
                            
                        # Create Section with timing
                        section = TestSection.objects.create(
                            mock_test=test, 
                            subject=subject,
                            section_name=section_name,
                            section_duration=section_duration,
                            section_order=section_order
                        )
                        section_order += 1
                        
                        for q_data in questions_data:
                            # Validate question text
                            if not q_data.get('text'):
                                print(f"Skipping question with missing text: {q_data}")
                                continue

                            # Find or create topic
                            topic_name = q_data.get('topic', 'General')
                            topic, _ = Topic.objects.get_or_create(name=topic_name, subject=subject, defaults={'slug': topic_name.lower().replace(' ', '-')})
                            
                            # Handle Question Grouping (for Charts/Graphs)
                            group = None
                            chart_data = q_data.get('chart_data')
                            
                            if chart_data:
                                import json
                                # Create a new group for this chart
                                group_type_map = {
                                    'bar': 'bar_chart',
                                    'line': 'line_graph',
                                    'pie': 'pie_chart',
                                    'table': 'table'
                                }
                                group_type = group_type_map.get(chart_data.get('type'), 'individual')
                                
                                group = QuestionGroup.objects.create(
                                    title=chart_data.get('title', f"Study the following {chart_data.get('type')} chart"),
                                    group_type=group_type,
                                    context_text=json.dumps(chart_data), # Store JSON data in context_text
                                    subject=subject,
                                    order=section_order * 100 # Simple ordering logic
                                )
                            
                            # Create Question
                            question = Question.objects.create(
                                topic=topic,
                                group=group, # Link to group if exists
                                text=q_data.get('text'),
                                option_a=q_data.get('option_a'),
                                option_b=q_data.get('option_b'),
                                option_c=q_data.get('option_c'),
                                option_d=q_data.get('option_d'),
                                option_e=q_data.get('option_e'),
                                correct_option=q_data.get('correct_option'),
                                explanation=q_data.get('explanation'),
                                difficulty=difficulty,
                                is_ai_generated=True
                            )
                            
                            # Link to Test with section
                            TestQuestion.objects.create(mock_test=test, question=question, section=section)
            else:
                # Subject-based configuration (SBI/IBPS)
                subject_config = config.get('subjects', {})
                total_questions = sum(subject_config.values())
                
                # Generate questions for each subject
                for sub_name, count in subject_config.items():
                    questions_data = generate_test_questions(sub_name, count, difficulty)
                    
                    if questions_data:
                        # Get or create subject
                        subject = Subject.objects.filter(name=sub_name).first()
                        if not subject:
                            continue
                            
                        # Create Section
                        section = TestSection.objects.create(mock_test=test, subject=subject)
                        
                        for q_data in questions_data:
                            # Validate question text
                            if not q_data.get('text'):
                                print(f"Skipping question with missing text: {q_data}")
                                continue

                            # Find or create topic
                            topic_name = q_data.get('topic', 'General')
                            topic, _ = Topic.objects.get_or_create(name=topic_name, subject=subject, defaults={'slug': topic_name.lower().replace(' ', '-')})
                            
                            # Create Question
                            question = Question.objects.create(
                                topic=topic,
                                text=q_data.get('text'),
                                option_a=q_data.get('option_a'),
                                option_b=q_data.get('option_b'),
                                option_c=q_data.get('option_c'),
                                option_d=q_data.get('option_d'),
                                option_e=q_data.get('option_e'),
                                correct_option=q_data.get('correct_option'),
                                explanation=q_data.get('explanation'),
                                difficulty=difficulty,
                                is_ai_generated=True
                            )
                            
                            # Link to Test
                            TestQuestion.objects.create(mock_test=test, question=question, section=section)
        else:
            # Fallback to default configuration if not found
            subject_config = {
                'English Language': 30,
                'Quantitative Aptitude': 35,
                'Reasoning Ability': 35
            }
            total_questions = sum(subject_config.values())
            
            # Generate questions for each subject
            for sub_name, count in subject_config.items():
                questions_data = generate_test_questions(sub_name, count, difficulty)
                
                if questions_data:
                    # Get or create subject
                    subject = Subject.objects.filter(name=sub_name).first()
                    if not subject:
                        continue
                        
                    # Create Section
                    section = TestSection.objects.create(mock_test=test, subject=subject)
                    
                    for q_data in questions_data:
                        # Validate question text
                        if not q_data.get('text'):
                            print(f"Skipping question with missing text: {q_data}")
                            continue

                        # Find or create topic
                        topic_name = q_data.get('topic', 'General')
                        topic, _ = Topic.objects.get_or_create(name=topic_name, subject=subject, defaults={'slug': topic_name.lower().replace(' ', '-')})
                        
                        # Create Question
                        question = Question.objects.create(
                            topic=topic,
                            text=q_data.get('text'),
                            option_a=q_data.get('option_a'),
                            option_b=q_data.get('option_b'),
                            option_c=q_data.get('option_c'),
                            option_d=q_data.get('option_d'),
                            option_e=q_data.get('option_e'),
                            correct_option=q_data.get('correct_option'),
                            explanation=q_data.get('explanation'),
                            difficulty=difficulty,
                            is_ai_generated=True
                        )
                        
                        # Link to Test
                        TestQuestion.objects.create(mock_test=test, question=question, section=section)
            
        
        messages.success(request, f"{exam_type} {stage} Mock Test with {total_questions} questions ({difficulty}) Generated Successfully!")
        return redirect('test_list')
        
    return render(request, 'tests/generate_test.html')

@login_required
def take_test(request, test_id):
    test = get_object_or_404(MockTest, id=test_id)
    test_questions = TestQuestion.objects.filter(mock_test=test).select_related('question', 'question__group', 'section').order_by('section__section_order', 'question__group__order', 'question__question_number_in_group', 'id')
    sections = TestSection.objects.filter(mock_test=test).order_by('section_order')
    
    if request.method == 'POST':
        score = 0.0
        correct = 0
        wrong = 0
        skipped = 0
        total_questions = test_questions.count()
        
        # Get exam configuration for negative marking
        config = EXAM_CONFIGURATIONS.get(test.exam_type, {}).get(test.stage, {})
        negative_mark = config.get('negative_marks', 0.25)
        
        # Create Attempt
        attempt = UserTestAttempt.objects.create(
            user=request.user,
            mock_test=test
        )
        
        for tq in test_questions:
            selected_option = request.POST.get(f'question_{tq.question.id}')
            is_correct = False
            
            if selected_option:
                if selected_option == tq.question.correct_option:
                    score += 1.0
                    correct += 1
                    is_correct = True
                else:
                    score -= negative_mark # Configurable negative marking
                    wrong += 1
            else:
                skipped += 1
            
            # Save Answer
            UserTestAnswer.objects.create(
                attempt=attempt,
                question=tq.question,
                selected_option=selected_option,
                is_correct=is_correct
            )
        
        # Update Attempt Stats
        attempt.score = score
        attempt.correct_count = correct
        attempt.wrong_count = wrong
        attempt.skipped_count = skipped
        attempt.save()
        
        messages.success(request, f"Test Completed! You scored {score}/{total_questions}.")
        return redirect('test_result', attempt_id=attempt.id)

    # Prepare data for JS
    questions_data = []
    for tq in test_questions:
        q = tq.question
        questions_data.append({
            'id': q.id,
            'text': q.text,
            'option_a': q.option_a,
            'option_b': q.option_b,
            'option_c': q.option_c,
            'option_d': q.option_d,
            'option_e': q.option_e,
            'section_name': tq.section.section_name if tq.section else 'General',
            'section_id': tq.section.id if tq.section else 0,
            'group_title': q.group.title if q.group else None,
            'group_context_text': q.group.context_text if q.group else None,
            'group_context_image': q.group.context_image.url if q.group and q.group.context_image else None
        })

    sections_data = []
    for section in sections:
        sections_data.append({
            'id': section.id,
            'name': section.section_name,
            'duration': section.section_duration
        })

    test_data = {
        'testId': test.id,
        'questions': questions_data,
        'sections': sections_data
    }

    return render(request, 'tests/take_test.html', {
        'test': test, 
        'test_questions': test_questions,
        'sections': sections,
        'test_data': test_data
    })


@login_required
def test_result(request, attempt_id):
    attempt = get_object_or_404(UserTestAttempt, id=attempt_id, user=request.user)
    answers = attempt.answers.select_related('question').all()
    
    context = {
        'attempt': attempt,
        'answers': answers,
        'test': attempt.mock_test
    }
    return render(request, 'tests/test_result.html', context)

@login_required
def test_history(request):
    attempts = UserTestAttempt.objects.filter(user=request.user).order_by('-completed_at')
    return render(request, 'tests/test_history.html', {'attempts': attempts})

@login_required
def delete_test(request, test_id):
    test = get_object_or_404(MockTest, id=test_id)
    # Optional: Check if the user owns the test or is an admin
    # if test.created_by != request.user: ...
    
    if request.method == 'POST':
        test.delete()
        messages.success(request, 'Test deleted successfully.')
        return redirect('test_list')
        
    return redirect('test_list')
