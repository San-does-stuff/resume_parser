from django.db import models
from django.contrib.auth.models import AbstractUser

class Users(AbstractUser):
    fullname = models.CharField(max_length=255,blank = True)
    phone = models.CharField(max_length = 20,blank = True)
    location = models.CharField(max_length = 255,blank = True)

    def __str__(self):
        return self.email
