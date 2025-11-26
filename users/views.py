from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now login.')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

from tests.models import UserTestAttempt
from django.db.models import Avg

@login_required
def dashboard(request):
    user_attempts = UserTestAttempt.objects.filter(user=request.user).select_related('mock_test')
    
    tests_attempted = user_attempts.count()
    
    # Calculate Average Score Percentage
    avg_score = 0
    if tests_attempted > 0:
        total_percentage = 0
        for attempt in user_attempts:
            if attempt.mock_test.total_marks > 0:
                total_percentage += (attempt.score / attempt.mock_test.total_marks) * 100
        avg_score = total_percentage / tests_attempted

    # Recent Activity
    recent_activity = user_attempts.order_by('-completed_at')[:5]
    
    context = {
        'tests_attempted': tests_attempted,
        'avg_score': avg_score,
        'recent_activity': recent_activity
    }
    return render(request, 'users/dashboard.html', context)

@login_required
def profile(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        target_exam = request.POST.get('target_exam')
        
        user = request.user
        user.email = email
        user.target_exam = target_exam
        user.save()
        
        messages.success(request, 'Your profile has been updated!')
        return redirect('profile')
        
    return render(request, 'users/profile.html')

@login_required
def study_plan(request):
    return render(request, 'users/study_plan.html')

@login_required
def analytics(request):
    return render(request, 'users/analytics.html')
