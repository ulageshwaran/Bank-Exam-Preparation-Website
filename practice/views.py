from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from exams.models import Subject, Topic
from .models import Question
from django.http import JsonResponse
import json
from ai_engine.ai_service import generate_question as ai_generate_question

@login_required
def generate_question_view(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    
    # Generate question using AI
    ai_data = ai_generate_question(topic.name, 'Medium')
    
    if ai_data:
        # Save to DB
        question = Question.objects.create(
            topic=topic,
            text=ai_data.get('text'),
            option_a=ai_data.get('option_a'),
            option_b=ai_data.get('option_b'),
            option_c=ai_data.get('option_c'),
            option_d=ai_data.get('option_d'),
            option_e=ai_data.get('option_e'),
            correct_option=ai_data.get('correct_option'),
            explanation=ai_data.get('explanation'),
            difficulty='Medium',
            is_ai_generated=True
        )
        return JsonResponse({'success': True, 'message': 'Question generated successfully!'})
    
    return JsonResponse({'success': False, 'message': 'Failed to generate question.'})

@login_required
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, 'practice/subject_list.html', {'subjects': subjects})

@login_required
def topic_list(request, subject_slug):
    subject = get_object_or_404(Subject, slug=subject_slug)
    topics = subject.topics.all()
    return render(request, 'practice/topic_list.html', {'subject': subject, 'topics': topics})

@login_required
def practice_session(request, topic_slug):
    # Handle potential duplicates gracefully
    topics = Topic.objects.filter(slug=topic_slug)
    if not topics.exists():
        from django.http import Http404
        raise Http404("Topic not found")
    topic = topics.first()
    questions = topic.questions.all()
    return render(request, 'practice/practice_session.html', {'topic': topic, 'questions': questions})

@login_required
def check_answer(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        question_id = data.get('question_id')
        selected_option = data.get('selected_option')
        
        question = get_object_or_404(Question, id=question_id)
        is_correct = question.correct_option == selected_option
        
        return JsonResponse({
            'is_correct': is_correct,
            'correct_option': question.correct_option,
            'explanation': question.explanation
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)
