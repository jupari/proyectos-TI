# Fase 01 — Modelo de datos y migraciones

**Rama:** `fase-01-modelo-datos` · **Depende de:** fase 00 · **Esfuerzo:** 1–2 sesiones

## Objetivo

Crear **todas** las tablas de `docs/modelo-datos.md`, con sus restricciones, índices, el
Django admin para poder inspeccionar los datos y un comando de datos de demostración.
Todavía no hay API de negocio.

## Precondiciones

- Fase 00 terminada: `docker compose up` funciona y `/api/v1/salud/` responde.
- Lee `docs/modelo-datos.md` completo antes de empezar. Es la especificación exacta.

---

## Pasos

### 1.1 Base común (`apps/core`)

1. `apps/core/models.py`:
   - `ModeloBase(models.Model)` abstracto con los seis campos de `docs/modelo-datos.md`
     (`id` UUID con `default=uuid4, editable=False, primary_key=True`, `creado_en`,
     `actualizado_en`, `creado_por`, `actualizado_por`, `activo`).
     `creado_por` y `actualizado_por` son `FK(settings.AUTH_USER_MODEL, null=True, blank=True,
     on_delete=models.SET_NULL, related_name="+")`.
   - `ManagerActivos(models.Manager)` cuyo `get_queryset()` filtra `activo=True`.
     En `ModeloBase` deja `objects = models.Manager()` y `activos = ManagerActivos()`.
     **Importante:** el primer manager declarado es el que usan las relaciones, así que el
     manager completo va primero.
   - `metodo eliminar_logico(self, usuario=None)` que pone `activo=False` y guarda.
2. `apps/core/choices.py`: todas las listas de opciones como clases `models.TextChoices`
   con etiquetas en español con tildes. Una clase por enumeración de `docs/modelo-datos.md`
   (`EstadoProyecto`, `Prioridad`, `EstadoTarea`, `TipoTarea`, `Periodicidad`,
   `EstadoAprobacion`, `Semaforo`, `CategoriaRubro`, `TipoRecurso`, `CategoriaDocumento`,
   `TipoEvento`, `EstadoCompromiso`, `EstadoHito`, `EstadoFase`, `TipoDependencia`,
   `ProveedorAuth`). **Ningún otro archivo define opciones sueltas.**
3. `apps/core/validators.py`: `validar_porcentaje` (0–100), `validar_positivo`,
   `validar_extension_archivo`, `validar_tamano_archivo`.

### 1.2 Usuarios y roles (`apps/accounts`)

4. `Usuario(AbstractUser)` según el modelo de datos: `USERNAME_FIELD = "email"`,
   `REQUIRED_FIELDS = ["nombres", "apellidos"]`, `username = None`, manager propio
   `UsuarioManager` con `create_user` y `create_superuser` por email.
5. `RolMeta` con `OneToOneField` a `auth.Group`.
6. Activa `AUTH_USER_MODEL = "accounts.Usuario"` en `config/settings/base.py`
   (quita el `TODO fase-01`).
7. Genera la migración inicial de `accounts` **antes** que las demás apps, porque todas
   dependen de ella.

### 1.3 Resto de las apps

Implementa en este orden, generando migraciones a medida (así las dependencias quedan bien):

8. `apps/catalogos`: `Area`, `Portafolio`, `PerfilRecurso`.
9. `apps/proyectos`: `Proyecto`, `FaseProyecto`, `Hito`, `RubroPresupuesto`.
10. `apps/recursos`: `Recurso`, `TarifaRecurso`, `AsignacionRecurso`.
11. `apps/tareas`: `Tarea`, `DependenciaTarea`.
12. `apps/ejecucion`: `RegistroEjecucion`, `GastoEjecutado`.
13. `apps/seguimiento`: `Seguimiento`, `CompromisoSeguimiento`.
14. `apps/expediente`: `DocumentoExpediente`, `EntradaBitacora`.

Para cada modelo, sin excepción:
- `class Meta` con `verbose_name`, `verbose_name_plural` (en español), `ordering` razonable,
  los `constraints` y los `indexes` que pide `docs/modelo-datos.md` §11.
- `__str__` legible (`f"{self.codigo} — {self.nombre}"`).
- `related_name` explícito en **toda** FK, en plural y en español (`proyecto.tareas`,
  `recurso.registros_ejecucion`).
- Campos calculados marcados `C` en el modelo de datos: los declaras como campos reales
  (para poder indexar y agregar) pero con `editable=False`, y los recalculas en `save()` o en
  el servicio correspondiente. **Nunca** se escriben desde la API.

### 1.4 Restricciones de base de datos

15. Traduce a `models.CheckConstraint` / `UniqueConstraint`:
    - `Proyecto`: `fecha_fin_plan >= fecha_inicio_plan`.
    - `FaseProyecto`: `UniqueConstraint(proyecto, orden)`.
    - `TarifaRecurso`: unicidad lógica de vigencias (el solape se valida en el servicio; en BD
      deja `UniqueConstraint(recurso, vigente_desde)`).
    - `AsignacionRecurso`: `UniqueConstraint(proyecto, recurso, fase, fecha_desde)` y
      `fecha_hasta >= fecha_desde`.
    - `Tarea`: `UniqueConstraint(proyecto, codigo)`.
    - `DependenciaTarea`: `UniqueConstraint(tarea_origen, tarea_destino)` y
      `CheckConstraint(~Q(tarea_origen=F("tarea_destino")))`.
    - `RegistroEjecucion`: `UniqueConstraint(recurso, proyecto, tarea, periodicidad,
      periodo_inicio)`, `CheckConstraint(horas > 0)`, `periodo_fin >= periodo_inicio`.
    - `Seguimiento`: `UniqueConstraint(proyecto, periodicidad, periodo_inicio)`.
    - `RolMeta`: `codigo` único.
    Nombra cada constraint de forma descriptiva (`proyecto_fin_despues_de_inicio`), porque el
    nombre aparece en el error que recibe el usuario.

### 1.5 Django admin

16. Registra **todos** los modelos con `list_display`, `list_filter`, `search_fields`,
    `date_hierarchy` donde aplique, `autocomplete_fields` para las FK con muchos registros y
    `readonly_fields` para los campos calculados y de auditoría.
17. Inlines útiles: `FaseProyecto`, `Hito`, `RubroPresupuesto` y `AsignacionRecurso` dentro de
    `Proyecto`; `TarifaRecurso` dentro de `Recurso`; `CompromisoSeguimiento` dentro de
    `Seguimiento`.
18. `EntradaBitacora` se registra con `has_add_permission = has_change_permission =
    has_delete_permission = False` (solo lectura).
19. Personaliza los títulos del admin: `admin.site.site_header = "Seguimiento de Proyectos TI"`.

### 1.6 Datos de demostración

20. `apps/core/management/commands/seed_demo.py`, **idempotente** (usa `get_or_create` y una
    semilla fija de `random` para que dos corridas den lo mismo), con el contenido que describe
    `docs/modelo-datos.md` §12.
21. Usa `factory-boy` en `apps/<x>/tests/factories.py` y reutiliza esas factories dentro del
    comando, para no tener dos formas de construir datos.
22. El comando acepta `--limpiar` para borrar los datos de demostración antes de recrearlos
    (nunca borra usuarios reales ni `is_superuser`).
23. Al terminar imprime un resumen: cuántos registros creó de cada tipo y las credenciales de
    los cinco usuarios de ejemplo.

### 1.7 Pruebas mínimas

24. Una prueba por restricción crítica, en `apps/<x>/tests/test_modelos.py`:
    - El proyecto con `fecha_fin_plan` anterior a la de inicio falla.
    - El registro de ejecución duplicado (mismo recurso, proyecto, tarea, periodo) falla.
    - El registro con `horas <= 0` falla.
    - La dependencia de una tarea consigo misma falla.
    - `__str__` de cada modelo no lanza excepción (una prueba parametrizada sobre las factories).

---

## Criterios de aceptación

- [x] `python manage.py migrate` aplica desde cero sobre una base vacía, sin errores.
- [x] `python manage.py makemigrations --check --dry-run` no detecta cambios pendientes.
- [x] Las entidades de `docs/modelo-datos.md` existen y se ven en `/admin/` — son **20**
      modelos con tabla propia (`tablero` no tiene tablas, por diseño). El documento y el
      README hablan de "22"; se deja constancia aquí en vez de inventar 2 entidades que no
      están especificadas, siguiendo la regla 1 de `PLAN.md` §4 ("No inventes entidades ni
      campos que no estén en `docs/modelo-datos.md`"). Si el conteo de 22 era intencional,
      hay que decirlo para actualizar primero `docs/modelo-datos.md`.
- [x] `python manage.py seed_demo` corre dos veces seguidas sin duplicar datos (verificado
      contando filas en BD, no solo el resumen impreso).
- [x] Tras `seed_demo` hay 4 proyectos, uno de ellos con semáforo rojo por sobrecosto
      (`PRY-2026-001`).
- [x] `pytest` verde, con las cinco pruebas de restricciones pedidas (fin < inicio, registro
      duplicado, horas ≤ 0, autodependencia, `__str__` parametrizado sobre las 19 factories +
      `RolMeta`).
- [x] `ruff check backend/` sin hallazgos.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend python manage.py migrate
docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo --limpiar
docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend ruff check .
```

## Fuera de alcance de esta fase

Serializers, ViewSets, permisos, autenticación, cualquier cosa del frontend. Las reglas de
negocio complejas (solapamiento de periodos, suma de pesos, ciclos de dependencias) se
**documentan** aquí pero se implementan en la fase del módulo que las usa; en esta fase solo
van las restricciones que viven en la base de datos.

## Evidencia

```
$ docker compose -f infra/docker-compose.yml exec backend python manage.py migrate
Operations to perform:
  Apply all migrations: accounts, admin, auth, catalogos, contenttypes, ejecucion, expediente,
  proyectos, recursos, seguimiento, sessions, tareas, token_blacklist
Running migrations:
  No migrations to apply.
(corrida previa, desde base vacía: las 8 migraciones iniciales de apps propias + las de
Django se aplicaron todas con "... OK", sin errores)

$ docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
No changes detected

$ docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo --limpiar
Limpiando datos de demostración previos...
Datos de demostración listos:
  usuarios: 5
  areas: 3
  portafolios: 2
  perfiles: 6
  recursos: 8
  proyectos: 4
  tareas: 40
  registros_ejecucion: 120
  gastos_ejecutados: 4
  seguimientos: 6
  documentos_expediente: 10

Credenciales de demostración (todas con la misma contraseña):
  [ADMIN] admin@seguimiento.local / Seguimiento2026!
  [PMO] pmo@seguimiento.local / Seguimiento2026!
  [LIDER] lider@seguimiento.local / Seguimiento2026!
  [RECURSO] recurso@seguimiento.local / Seguimiento2026!
  [CONSULTA] consulta@seguimiento.local / Seguimiento2026!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo
(segunda corrida, mismos conteos — confirmado también contando filas en BD directamente,
no solo el resumen impreso: Proyecto=4, Tarea=40, RegistroEjecucion=120, Seguimiento=6,
CompromisoSeguimiento=6, DocumentoExpediente=10, Recurso=8, TarifaRecurso=8,
AsignacionRecurso=8, Area=3, Portafolio=2, PerfilRecurso=6, Usuario=5 — ninguno se duplicó)

$ docker compose -f infra/docker-compose.yml exec backend python manage.py shell -c "..."
Proyectos: 4
  PRY-2026-001 EJECUCION ROJO
  PRY-2026-002 EJECUCION VERDE
  PRY-2026-003 CERRADO VERDE
  PRY-2026-004 BORRADOR VERDE

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................                                               [100%]
24 passed in 10.76s

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py check
System check identified no issues (0 silenced).
```

Modelos registrados en `/admin/` (20, ver nota en los criterios de aceptación sobre el
conteo de "22"):

```
Area, AsignacionRecurso, CompromisoSeguimiento, DependenciaTarea, DocumentoExpediente,
EntradaBitacora, FaseProyecto, GastoEjecutado, Hito, PerfilRecurso, Portafolio, Proyecto,
Recurso, RegistroEjecucion, RolMeta, RubroPresupuesto, Seguimiento, Tarea, TarifaRecurso,
Usuario
```
