# Generated by Django 5.1.4 on 2024-12-22 10:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characteritemequipment',
            name='item_base_option',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='characters.itembaseoption'),
        ),
    ]
