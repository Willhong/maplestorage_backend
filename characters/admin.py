from django.contrib import admin

from .models import CharacterBasic, ItemEquipment, Symbol, Skill, Title

# Register your models here.

admin.site.register(CharacterBasic)
admin.site.register(ItemEquipment)
admin.site.register(Symbol)
admin.site.register(Skill)
admin.site.register(Title)
