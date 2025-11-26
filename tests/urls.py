from django.urls import path
from . import views

urlpatterns = [
    path('', views.test_list, name='test_list'),
    path('generate/', views.generate_test_view, name='generate_test'),
    path('<int:test_id>/take/', views.take_test, name='take_test'),
    path('result/<int:attempt_id>/', views.test_result, name='test_result'),
    path('history/', views.test_history, name='test_history'),
    path('delete/<int:test_id>/', views.delete_test, name='delete_test'),
]
