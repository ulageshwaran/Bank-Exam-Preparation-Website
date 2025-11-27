from django.db import models
from exams.models import Topic, Subject
from django.conf import settings

class QuestionGroup(models.Model):
    """
    Represents a group of related questions (e.g., 5 questions based on a single graph/chart/puzzle)
    """
    GROUP_TYPE_CHOICES = [
        ('number_series', 'Number Series'),
        ('line_graph', 'Line Graph'),
        ('bar_chart', 'Bar Chart'),
        ('pie_chart', 'Pie Chart'),
        ('table', 'Table/Data Interpretation'),
        ('missing_data', 'Missing Data Table'),
        ('puzzle', 'Puzzle (Floor/Flat/Arrangement)'),
        ('alphanumeric', 'Alphanumeric Series'),
        ('coding', 'Coding-Decoding'),
        ('seating', 'Seating Arrangement'),
        ('scheduling', 'Scheduling/Day Arrangement'),
        ('paragraph', 'Paragraph/Comprehension'),
        ('individual', 'Individual Question'),
    ]
    
    title = models.CharField(max_length=500, help_text="e.g., 'Study the following line graph and answer questions 6-10'")
    group_type = models.CharField(max_length=20, choices=GROUP_TYPE_CHOICES, default='individual')
    context_text = models.TextField(blank=True, help_text="Problem statement, table data, series pattern, or puzzle description")
    context_image = models.ImageField(upload_to='question_groups/', blank=True, null=True, help_text="Graph/chart/diagram image")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='question_groups')
    order = models.IntegerField(default=0, help_text="Order of this group in the test")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.get_group_type_display()} - {self.title[:50]}"



class Question(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]
    
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='questions')
    group = models.ForeignKey(QuestionGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions', help_text="Question group this question belongs to")
    question_number_in_group = models.IntegerField(default=1, help_text="Position of this question within its group (1-5 typically)")
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    option_e = models.CharField(max_length=255, blank=True, null=True) # Banking exams often have 5 options
    correct_option = models.CharField(max_length=1, choices=[
        ('A', 'Option A'),
        ('B', 'Option B'),
        ('C', 'Option C'),
        ('D', 'Option D'),
        ('E', 'Option E'),
    ])
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    is_ai_generated = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['group__order', 'question_number_in_group', 'id']

    def __str__(self):
        return self.text[:50]

class PracticeSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.topic.name}"
