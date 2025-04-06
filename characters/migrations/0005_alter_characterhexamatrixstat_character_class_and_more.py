# Generated by Django 5.1.4 on 2025-03-27 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0004_alter_charactercashitemequipment_character_look_mode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_class',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core',
            field=models.ManyToManyField(blank=True, null=True, related_name='core_1', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core_2',
            field=models.ManyToManyField(blank=True, null=True, related_name='core_2', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core_3',
            field=models.ManyToManyField(blank=True, null=True, related_name='core_3', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core',
            field=models.ManyToManyField(blank=True, null=True, related_name='preset_core_1', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core_2',
            field=models.ManyToManyField(blank=True, null=True, related_name='preset_core_2', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core_3',
            field=models.ManyToManyField(blank=True, null=True, related_name='preset_core_3', to='characters.hexastatcore'),
        ),
    ]
