from django.contrib import admin

# Register your models here.

from .models import Account, Character

admin.site.register(Account)
admin.site.register(Character)
