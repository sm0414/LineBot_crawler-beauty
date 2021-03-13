from django.db import models

# Create your models here.
class CrawlerBeauty(models.Model):
	page = models.IntegerField()
	result = models.CharField(max_length=2000)