import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proyectos', '0006_en_produccion_en_soporte'),
        ('tareas', '0002_tarea_clave_jira'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sprint',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('activo', models.BooleanField(default=True)),
                (
                    'actualizado_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='+',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'creado_por',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='+',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ('id_jira', models.PositiveIntegerField()),
                ('nombre', models.CharField(max_length=200)),
                (
                    'estado',
                    models.CharField(
                        choices=[('FUTURO', 'Futuro'), ('ACTIVO', 'Activo'), ('CERRADO', 'Cerrado')],
                        default='FUTURO',
                        max_length=10,
                    ),
                ),
                ('fecha_inicio', models.DateField(blank=True, null=True)),
                ('fecha_fin', models.DateField(blank=True, null=True)),
                ('fecha_cierre', models.DateField(blank=True, null=True)),
                ('meta', models.TextField(blank=True)),
                (
                    'proyecto',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='sprints',
                        to='proyectos.proyecto',
                    ),
                ),
            ],
            options={
                'verbose_name': 'sprint',
                'verbose_name_plural': 'sprints',
                'ordering': ['proyecto', '-fecha_inicio', 'nombre'],
            },
        ),
        migrations.AddConstraint(
            model_name='sprint',
            constraint=models.UniqueConstraint(
                fields=('proyecto', 'id_jira'), name='sprint_jira_unico'
            ),
        ),
        migrations.AddField(
            model_name='tarea',
            name='sprint',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tareas',
                to='tareas.sprint',
            ),
        ),
        migrations.AddField(
            model_name='tarea',
            name='epica_clave',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='tarea',
            name='epica_nombre',
            field=models.CharField(blank=True, default='', max_length=250),
        ),
        migrations.AlterField(
            model_name='tarea',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('ACTIVIDAD', 'Actividad'),
                    ('TAREA', 'Tarea'),
                    ('INCIDENCIA', 'Incidencia'),
                    ('CAMBIO', 'Cambio'),
                    ('REUNION', 'Reunión'),
                    ('HISTORIA', 'Historia de usuario'),
                ],
                default='TAREA',
                max_length=20,
            ),
        ),
    ]
