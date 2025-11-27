from django.contrib import admin
from .models import Question, QuestionGroup, PracticeSession

@admin.register(QuestionGroup)
class QuestionGroupAdmin(admin.ModelAdmin):
    list_display = ['title', 'group_type', 'subject', 'order', 'created_at']
    list_filter = ['group_type', 'subject']
    search_fields = ['title', 'context_text']
    ordering = ['order', 'created_at']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'topic', 'group', 'question_number_in_group', 'difficulty', 'is_ai_generated']
    list_filter = ['difficulty', 'is_ai_generated', 'topic__subject']
    search_fields = ['text']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question'

@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'score', 'total_questions', 'completed_at']
    list_filter = ['completed_at', 'topic']
    search_fields = ['user__username']
