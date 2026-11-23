from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0006_en_produccion_en_soporte'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='avance_tareas',
            field=models.DecimalField(
                blank=True, decimal_places=2, editable=False, max_digits=5, null=True
            ),
        ),
        migrations.AddField(
            model_name='proyecto',
            name='avance_desde_tareas',
            field=models.BooleanField(default=False),
        ),
    ]
