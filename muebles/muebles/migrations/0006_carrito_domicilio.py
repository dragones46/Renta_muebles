# Generated by Django 5.1.7 on 2025-03-25 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('muebles', '0005_alter_mueble_precio_diario'),
    ]

    operations = [
        migrations.AddField(
            model_name='carrito',
            name='domicilio',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
