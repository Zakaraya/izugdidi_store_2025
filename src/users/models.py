from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone = models.CharField(max_length=40, blank=True)
    receive_marketing = models.BooleanField(default=False)

    def __str__(self):
        return self.username or f"User#{self.pk}"
