# Generated by Django 4.2.6 on 2025-03-14 15:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('muebles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='renta',
            name='duracion_anios',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='renta',
            name='duracion_meses',
            field=models.IntegerField(default=0),
        ),
    ]
