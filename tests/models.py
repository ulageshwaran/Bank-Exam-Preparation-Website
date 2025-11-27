from django.db import models
from exams.models import Exam, Subject
from practice.models import Question
from django.conf import settings

class MockTest(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    EXAM_TYPE_CHOICES = [
        ('SBI', 'SBI Clerk'),
        ('IBPS', 'IBPS Clerk'),
        ('RRB', 'RRB Clerk'),
    ]
    STAGE_CHOICES = [
        ('Prelims', 'Prelims'),
        ('Mains', 'Mains'),
    ]
    title = models.CharField(max_length=200)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    duration = models.IntegerField(help_text="Duration in minutes")
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    exam_type = models.CharField(max_length=10, choices=EXAM_TYPE_CHOICES, default='SBI')
    stage = models.CharField(max_length=10, choices=STAGE_CHOICES, default='Prelims')
    total_marks = models.FloatField(default=100.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class TestSection(models.Model):
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='sections')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    section_name = models.CharField(max_length=100, default='Section', help_text="e.g., 'Numerical Ability', 'Reasoning Ability'")
    section_duration = models.IntegerField(default=20, help_text="Duration in minutes for this section")
    section_order = models.IntegerField(default=1, help_text="Order of this section in the test (1, 2, 3...)")
    
    class Meta:
        ordering = ['section_order']
    
    def __str__(self):
        return f"{self.mock_test.title} - {self.section_name}"


class TestQuestion(models.Model):
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='test_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    section = models.ForeignKey(TestSection, on_delete=models.CASCADE, null=True, blank=True, related_name='questions')
    
    class Meta:
        ordering = ['section__section_order', 'question__group__order', 'question__question_number_in_group', 'id']
    
class UserTestAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)
    correct_count = models.IntegerField(default=0)
    wrong_count = models.IntegerField(default=0)
    skipped_count = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

class UserTestAnswer(models.Model):
    attempt = models.ForeignKey(UserTestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    def get_selected_option_text(self):
        if not self.selected_option:
            return None
        return getattr(self.question, f'option_{self.selected_option.lower()}', None)

    def get_correct_option_text(self):
        if not self.question.correct_option:
            return None
        return getattr(self.question, f'option_{self.question.correct_option.lower()}', None)
