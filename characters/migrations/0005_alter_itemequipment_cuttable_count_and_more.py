# Generated by Django 5.1.4 on 2025-03-21 15:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0004_rename_scroll_upgradable_count_itemequipment_scroll_upgradeable_count'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itemequipment',
            name='cuttable_count',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='golden_hammer_flag',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='item_etc_option',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='characters.itemetcoption'),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='item_starforce_option',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='characters.itemstarforceoption'),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='scroll_resilience_count',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='scroll_upgrade',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='starforce',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='itemequipment',
            name='starforce_scroll_flag',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
