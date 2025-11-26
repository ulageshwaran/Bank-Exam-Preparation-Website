from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    target_exam = forms.ChoiceField(choices=[
        ('SBI PO', 'SBI PO'),
        ('IBPS PO', 'IBPS PO'),
        ('IBPS Clerk', 'IBPS Clerk'),
        ('RBI Grade B', 'RBI Grade B'),
        ('SSC CGL', 'SSC CGL')
    ])

    class Meta:
        model = User
        fields = ['username', 'email', 'target_exam']
