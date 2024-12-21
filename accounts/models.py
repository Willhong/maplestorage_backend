from django.db import models
from django.contrib.auth.models import User


class Account(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_id = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)


class Character(models.Model):
    account = models.ForeignKey(
        Account, related_name='characters', on_delete=models.CASCADE, null=True)
    ocid = models.CharField(max_length=255, unique=True)
    character_name = models.CharField(max_length=255)
    world_name = models.CharField(max_length=255, null=True, blank=True)
    character_class = models.CharField(max_length=255, null=True, blank=True)
    character_level = models.IntegerField(null=True, blank=True)


class MapleStoryAPIKey(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='api_keys', null=True, blank=True)
    api_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
