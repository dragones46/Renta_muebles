# Generated by Django 5.1.7 on 2025-04-02 16:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('muebles', '0015_alter_pregunta_options_pregunta_fecha_eliminacion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='faq',
            name='categoria',
            field=models.CharField(choices=[('CUENTA', 'Cuenta de usuario'), ('PAGOS', 'Pagos y facturación'), ('ENTREGAS', 'Entregas y logística'), ('MUEBLES', 'Productos y muebles'), ('SISTEMA', 'Sistema y mantenimiento'), ('OTROS', 'Otros')], max_length=50),
        ),
    ]
