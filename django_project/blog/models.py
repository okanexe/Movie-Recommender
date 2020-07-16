from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse


# class Profile(models.Model):
#     name = models.CharField(max_length=150)
#     title = models.CharField(max_length=50)
#
#     def __str__(self):
#         return self.name


class Movies(models.Model):
    imdb_id = models.CharField(max_length=1500)
    title = models.CharField(max_length=2000)
    overview = models.CharField(max_length=20000)
    genre = models.CharField(max_length=4000)
    IMDBScore = models.FloatField()

    def __str__(self):
        return self.title
