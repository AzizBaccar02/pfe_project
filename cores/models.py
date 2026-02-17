from django.db import models

# Create your models here.
class Localisation(models.Model):
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    postalCode = models.CharField(max_length=30)