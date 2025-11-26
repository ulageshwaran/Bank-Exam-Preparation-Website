from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    bio = models.TextField(blank=True)
    target_exam = models.CharField(max_length=100, blank=True)
    subscription_status = models.BooleanField(default=False)

    def __str__(self):
        return self.username
