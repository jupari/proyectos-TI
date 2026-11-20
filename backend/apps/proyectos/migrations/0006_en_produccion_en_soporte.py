from django.db import migrations, models


def pasar_fase_a_casillas(apps, schema_editor):
    Proyecto = apps.get_model("proyectos", "Proyecto")
    Proyecto.objects.filter(fase_operacion="PRODUCCION").update(en_produccion=True)
    Proyecto.objects.filter(fase_operacion="SOPORTE").update(en_soporte=True)


def pasar_casillas_a_fase(apps, schema_editor):
    Proyecto = apps.get_model("proyectos", "Proyecto")
    Proyecto.objects.filter(en_soporte=True).update(fase_operacion="SOPORTE")
    Proyecto.objects.filter(en_produccion=True).update(fase_operacion="PRODUCCION")


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0005_proyecto_fase_operacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='proyecto',
            name='en_produccion',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='proyecto',
            name='en_soporte',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(pasar_fase_a_casillas, pasar_casillas_a_fase),
        migrations.RemoveField(
            model_name='proyecto',
            name='fase_operacion',
        ),
    ]
