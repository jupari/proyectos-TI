from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0004_entregablehito'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='fase_operacion',
            field=models.CharField(
                blank=True,
                choices=[('PRODUCCION', 'Producción'), ('SOPORTE', 'Soporte')],
                default='',
                max_length=12,
            ),
        ),
    ]
