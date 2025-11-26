from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ai_engine.ai_service import generate_test_questions
from .models import MockTest, TestSection, TestQuestion, UserTestAttempt, UserTestAnswer
from exams.models import Exam, Subject
from practice.models import Question, Topic
import threading

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
            duration=60 if stage == 'Prelims' else 180, 
            difficulty=difficulty,
            exam_type=exam_type,
            stage=stage
        )
        
        # Generating full questions
        # This might take some time (approx 60-90s)
        
        # Default Configuration (SBI/IBPS Prelims)
        subject_config = {
            'English Language': 30,
            'Quantitative Aptitude': 35,
            'Reasoning Ability': 35
        }
        
        # RRB Prelims Configuration (No English, 40/40)
        if exam_type == 'RRB' and stage == 'Prelims':
            subject_config = {
                'Quantitative Aptitude': 40,
                'Reasoning Ability': 40
            }
            test.duration = 45 # RRB Prelims is usually 45 mins
            test.save()
            
        # Mains Configuration (Placeholder logic for now)
        if stage == 'Mains':
             # Mains usually has more questions and sections (GA, Computer), 
             # but for MVP we stick to core subjects with higher difficulty
             difficulty = 'Hard'
             # You might want to adjust counts here too
        
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
                    TestQuestion.objects.create(mock_test=test, question=question)
        
        messages.success(request, f"Mock Test ({difficulty}) Generated Successfully!")
        return redirect('test_list')
        
    return render(request, 'tests/generate_test.html')

@login_required
def take_test(request, test_id):
    test = get_object_or_404(MockTest, id=test_id)
    test_questions = TestQuestion.objects.filter(mock_test=test).select_related('question')
    
    if request.method == 'POST':
        score = 0.0
        correct = 0
        wrong = 0
        skipped = 0
        total_questions = test_questions.count()
        
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
                    score -= 0.25 # Negative marking
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

    return render(request, 'tests/take_test.html', {'test': test, 'test_questions': test_questions})

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
