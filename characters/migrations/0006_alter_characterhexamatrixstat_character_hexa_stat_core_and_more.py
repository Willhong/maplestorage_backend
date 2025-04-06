# Generated by Django 5.1.4 on 2025-03-27 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('characters', '0005_alter_characterhexamatrixstat_character_class_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core',
            field=models.ManyToManyField(related_name='core_1', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core_2',
            field=models.ManyToManyField(related_name='core_2', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='character_hexa_stat_core_3',
            field=models.ManyToManyField(related_name='core_3', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core',
            field=models.ManyToManyField(related_name='preset_core_1', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core_2',
            field=models.ManyToManyField(related_name='preset_core_2', to='characters.hexastatcore'),
        ),
        migrations.AlterField(
            model_name='characterhexamatrixstat',
            name='preset_hexa_stat_core_3',
            field=models.ManyToManyField(related_name='preset_core_3', to='characters.hexastatcore'),
        ),
    ]
