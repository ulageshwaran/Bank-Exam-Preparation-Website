from django.urls import path
from . import views

urlpatterns = [
    path('', views.subject_list, name='practice_home'),
    path('subject/<slug:subject_slug>/', views.topic_list, name='topic_list'),
    path('topic/<path:topic_slug>/', views.practice_session, name='practice_session'),
    path('api/check_answer/', views.check_answer, name='check_answer'),
    path('api/generate_question/<int:topic_id>/', views.generate_question_view, name='generate_question'),
]
