# Plan maestro — Seguimiento de Proyectos de TI

> **Para el modelo que ejecuta:** este archivo es la fuente de verdad. Antes de escribir
> una línea de código, lee: este archivo, [docs/modelo-datos.md](docs/modelo-datos.md) y
> [docs/api-contrato.md](docs/api-contrato.md). Luego abre **solo** el archivo de la fase que
> te pidieron ejecutar (`docs/plan/fase-NN-*.md`) y sigue sus pasos en orden.
> No ejecutes una fase si la anterior no cumple su "Definición de terminado".

---

## 1. Objetivo

Panel administrativo web para hacer seguimiento a los proyectos de TI, con control de la
ejecución presupuestal en **horas** y en **dinero**, ingesta periódica (diaria / semanal /
mensual) de la ejecución de recursos, gestión de tareas y su programación, y un
**expediente digital** por proyecto donde quede documentado todo el seguimiento.

Objetivos funcionales del usuario, trazados a las fases que los cubren:

| # | Objetivo | Fases |
|---|----------|-------|
| 1 | Seguimiento de proyectos de TI | 05, 08, 09 |
| 1.2 | Tablero de control con ejecución presupuestal en horas y dinero | 10 |
| 1.3 | Ingesta de recursos y seguimiento mensual / semanal / diario | 06, 08 |
| 1.4 | Adicionar tareas o actividades durante la ejecución | 07 |
| 1.5 | Expediente digital con seguimiento, tareas y su ejecución | 09 |
| 2 | Login con JWT y OAuth 2.0 (Google) | 03 |
| 3 | Sistema de roles básico | 03 |
| 4 | CRUDs e interfaces necesarias | 04 a 09 |
| 5 | Panel administrativo: planeado vs. ejecutado | 08, 10 |
| 6 | Horas reales importadas desde Jira/Tempo, además del registro manual | 12 |

---

## 2. Stack fijado (no cambiar sin actualizar este archivo)

**Backend**
- Python 3.12, **Django 5.x + Django REST Framework**
- PostgreSQL 16 (`psycopg[binary]`)
- `djangorestframework-simplejwt` (JWT con rotación y blacklist)
- `django-filter` (filtros de lista), `drf-spectacular` (OpenAPI + Swagger UI)
- `django-cors-headers`, `django-environ`
- `google-auth` + `requests` (verificación de tokens de Google)
- `pytest` + `pytest-django` + `factory-boy` (pruebas), `ruff` (lint + formato)

**Frontend**
- **Angular** (última estable que instale `ng new`), **standalone components + signals**, sin NgModules
- **Tailwind CSS 3.4** y **componentes propios** (no Material, no PrimeNG)
- `HttpClient` con interceptores funcionales, guards funcionales, Reactive Forms tipados
- `chart.js` 4 envuelto en un componente propio, solo para la fase 10

**Autenticación**
- JWT propio (usuario/clave) **y** Google OAuth 2.0 con Authorization Code + PKCE.
  El frontend obtiene el `code`, el backend lo canjea y devuelve **siempre** tokens propios.
  El resto de la app solo conoce el JWT propio.

**Infraestructura**
- Docker Compose: `db` (Postgres), `backend` (Django), `frontend` (Angular dev server o Nginx)
- Un solo `docker compose up` debe levantar el entorno completo de desarrollo.

> **Regla de versiones:** en la fase 00, después de instalar, escribe las versiones reales
> en `docs/STACK-LOCK.md` (Python, Django, DRF, Node, Angular CLI, Tailwind, Postgres).
> Las fases siguientes se ajustan a lo que diga ese archivo, no a la memoria del modelo.

---

## 3. Estructura del repositorio

```
Seguimiento-pry/
├─ PLAN.md                      # este archivo
├─ README.md                    # cómo levantar el proyecto
├─ .env.example                 # plantilla de variables (nunca subir .env)
├─ docs/
│  ├─ modelo-datos.md           # entidades, campos, reglas de negocio
│  ├─ api-contrato.md           # endpoints, payloads, permisos, errores
│  ├─ STACK-LOCK.md             # versiones realmente instaladas (fase 00)
│  └─ plan/fase-00..12-*.md     # una fase por archivo
├─ infra/
│  ├─ docker-compose.yml
│  ├─ docker-compose.override.yml
│  ├─ backend.Dockerfile
│  ├─ frontend.Dockerfile
│  └─ nginx/default.conf
├─ backend/
│  ├─ manage.py
│  ├─ pyproject.toml            # dependencias + config de ruff y pytest
│  ├─ config/
│  │  ├─ settings/{base,dev,prod}.py
│  │  └─ urls.py  asgi.py  wsgi.py
│  └─ apps/
│     ├─ core/        # modelos base, mixins, paginación, errores, auditoría
│     ├─ accounts/    # Usuario, roles, login JWT, Google OAuth
│     ├─ catalogos/   # Area, Portafolio, PerfilRecurso
│     ├─ recursos/    # Recurso, TarifaRecurso, AsignacionRecurso
│     ├─ proyectos/   # Proyecto, FaseProyecto, Hito, RubroPresupuesto
│     ├─ tareas/      # Tarea, DependenciaTarea
│     ├─ ejecucion/   # RegistroEjecucion, GastoEjecutado
│     ├─ seguimiento/ # Seguimiento, CompromisoSeguimiento
│     ├─ expediente/  # DocumentoExpediente, EntradaBitacora
│     └─ tablero/     # endpoints de solo lectura con KPIs
└─ frontend/
   └─ src/app/
      ├─ core/        # auth, http, guards, interceptores, modelos, config
      ├─ shared/      # ui/ (componentes propios), pipes, directivas, utils
      ├─ layout/      # shell: sidebar, topbar, breadcrumbs
      └─ features/
         ├─ auth/ dashboard/ proyectos/ tareas/ recursos/
         └─ ejecucion/ seguimientos/ expediente/ admin/
```

---

## 4. Convenciones obligatorias

**Idioma**
- Dominio (modelos, campos, endpoints, rutas, textos de UI): **español sin tildes en
  identificadores** (`fecha_fin_plan`, `horas_ejecutadas`, `/api/v1/proyectos/`).
- Palabras estructurales del framework en inglés (`serializers.py`, `ViewSet`, `signal`).
- Comentarios y mensajes de error visibles: español con tildes.

**Backend**
- Toda la API vive bajo `/api/v1/`. Nada de endpoints fuera de ese prefijo.
- Un `ModelViewSet` por entidad con CRUD, salvo que la fase diga lo contrario.
- Todo modelo hereda de `core.models.ModeloBase` (`id` UUID, `creado_en`, `actualizado_en`,
  `creado_por`, `actualizado_por`, `activo`).
- Borrado **lógico** por defecto (`activo=False`); borrado físico solo donde la fase lo diga.
- Serializers separados para lectura y escritura cuando el de lectura traiga datos anidados
  (`ProyectoSerializer` / `ProyectoEscrituraSerializer`).
- Paginación global: `PageNumberPagination`, `page_size=25`, parámetro `?page_size=` hasta 200.
- Filtros, búsqueda y orden con `django-filter` + `SearchFilter` + `OrderingFilter`.
- Todo cálculo monetario con `Decimal` y `DecimalField(max_digits=18, decimal_places=2)`.
  Horas: `DecimalField(max_digits=10, decimal_places=2)`. **Nunca `float` para dinero.**
- Zona horaria `America/Bogota`, `USE_TZ=True`. Las fechas de negocio son `DateField`
  (sin hora); las de auditoría son `DateTimeField`.
- Formato de error único, definido en `docs/api-contrato.md` §8.

**Frontend**
- Componentes `standalone`, estado con `signal()` / `computed()`, `ChangeDetectionStrategy.OnPush`.
- Carga diferida por feature con `loadChildren` y archivos `*.routes.ts`.
- Un servicio por recurso en `features/<x>/data/<x>.service.ts`; los componentes **no**
  llaman a `HttpClient` directamente.
- Modelos TypeScript en `core/models/`, con nombres de campo **idénticos** al JSON del backend.
- Sin `any`. `strict: true` en `tsconfig.json`.
- Componentes propios obligatorios en `shared/ui/` (fase 04): botón, input, select, datepicker,
  textarea, tabla con paginación y orden, modal, drawer, tabs, badge, card, toast, diálogo de
  confirmación, spinner, estado vacío, barra de progreso, semáforo, migas de pan.
  **Las fases siguientes reutilizan estos componentes, no crean variantes nuevas.**
- Tokens de diseño (colores, radios, sombras, tipografía) centralizados en `tailwind.config.js`.
  Nada de colores sueltos tipo `bg-[#3b82f6]` en las plantillas.

**Git**
- Una rama por fase: `fase-00-infraestructura`, `fase-01-modelo-datos`, …
- Commits pequeños, en español imperativo (`agrega modelo Proyecto`).
- Un commit final por fase con el resumen de la definición de terminado.

**Reglas de alcance para el ejecutor**
1. No inventes entidades ni campos que no estén en `docs/modelo-datos.md`.
   Si falta algo, **primero** actualiza ese documento, explica el cambio y luego impleméntalo.
2. No adelantes trabajo de fases posteriores "porque ya estás ahí".
3. Si un paso falla dos veces seguidas, detente y reporta el error con el log completo;
   no improvises una solución que cambie el stack.
4. Al cerrar cada fase, escribe en su archivo, sección "Evidencia", la salida real de los
   comandos de verificación.

---

## 5. Roles y permisos (sistema básico)

Los roles se implementan sobre `django.contrib.auth.models.Group` más un modelo `RolMeta`
(código, descripción, es_sistema). Se siembran en la fase 03.

| Código | Nombre | Puede |
|--------|--------|-------|
| `ADMIN` | Administrador | Todo, incluida la administración de usuarios, roles y catálogos |
| `PMO` | PMO / Dirección | Ver todos los proyectos, crearlos, aprobar ejecución, publicar seguimientos |
| `LIDER` | Líder de proyecto | CRUD completo **solo en sus proyectos** (es gerente o líder técnico) |
| `RECURSO` | Recurso / Ejecutor | Ver los proyectos donde está asignado, registrar su propia ejecución de horas, actualizar sus tareas |
| `CONSULTA` | Consulta | Solo lectura de proyectos, tablero y expediente |

Dos capas de control: permiso de objeto (`EsLiderDelProyecto`, `EsDuenoDelRegistro`) y
filtrado del `queryset` por rol, para que un `RECURSO` no vea en los listados lo que no le
corresponde. La matriz completa está en `docs/api-contrato.md` §7.

---

## 6. Variables de entorno (`.env.example`)

```
# Postgres
POSTGRES_DB=seguimiento
POSTGRES_USER=seguimiento
POSTGRES_PASSWORD=cambiar_en_local
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Django
DJANGO_SETTINGS_MODULE=config.settings.dev
DJANGO_SECRET_KEY=cambiar_en_local
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://localhost:4200
TIME_ZONE=America/Bogota
MONEDA_BASE=COP

# JWT
JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=7

# Google OAuth 2.0
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:4200/auth/google/callback
GOOGLE_DOMINIOS_PERMITIDOS=

# Archivos del expediente
MEDIA_ROOT=/app/media
MAX_UPLOAD_MB=25
EXTENSIONES_PERMITIDAS=pdf,docx,xlsx,pptx,png,jpg,jpeg,msg,txt,csv,zip

# Frontend
API_BASE_URL=http://localhost:8000/api/v1

# Integración Jira + Tempo (fase 12; dejar vacío si no se usa)
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
TEMPO_API_TOKEN=
```

---

## 7. Mapa de fases

| Fase | Nombre | Depende de | Entregable verificable |
|------|--------|-----------|------------------------|
| [00](docs/plan/fase-00-infraestructura.md) | Infraestructura y andamiaje | — | `docker compose up` levanta db, backend y frontend; `/api/v1/salud/` responde 200 |
| [01](docs/plan/fase-01-modelo-datos.md) | Modelo de datos y migraciones | 00 | Migraciones aplican; el admin muestra todas las entidades; `seed_demo` carga datos |
| [02](docs/plan/fase-02-nucleo-api.md) | Núcleo de la API | 01 | Paginación, filtros, errores uniformes, OpenAPI en `/api/schema/swagger/`, auditoría activa |
| [03](docs/plan/fase-03-auth-roles.md) | Autenticación JWT + Google + roles | 02 | Login con clave y con Google devuelve JWT propio; permisos por rol probados |
| [04](docs/plan/fase-04-shell-frontend.md) | Shell del frontend y UI base | 03 | Login funcional, layout con menú, catálogo con los 18 componentes de `shared/ui` |
| [05](docs/plan/fase-05-proyectos-presupuesto.md) | Proyectos, fases, hitos y presupuesto | 04 | CRUD de proyectos con presupuesto en horas y dinero, de punta a punta |
| [06](docs/plan/fase-06-recursos-asignacion.md) | Recursos, tarifas y asignación planeada | 05 | CRUD de recursos y asignaciones; costo planeado calculado |
| [07](docs/plan/fase-07-tareas-programacion.md) | Tareas, actividades y programación | 06 | Alta de tareas durante la ejecución, jerarquía, dependencias, cronograma |
| [08](docs/plan/fase-08-ejecucion-ingesta.md) | Ingesta de ejecución (horas y gastos) | 07 | Registro diario, semanal y mensual; aprobación; planeado vs. ejecutado |
| [09](docs/plan/fase-09-seguimiento-expediente.md) | Seguimientos y expediente digital | 08 | Seguimiento periódico publicable, adjuntos versionados, línea de tiempo |
| [10](docs/plan/fase-10-tablero-control.md) | Tablero de control y reportes | 09 | KPIs, semáforos, gráficos de ejecución, exportación a CSV |
| [11](docs/plan/fase-11-calidad-despliegue.md) | Calidad, pruebas y despliegue | 10 | Cobertura ≥70% en backend, e2e del flujo crítico, imagen de producción |
| [12](docs/plan/fase-12-integracion-jira.md) | Importación de horas desde Jira/Tempo | 08 | `importar_horas_jira --desde --hasta` trae worklogs de Tempo como `RegistroEjecucion` pendientes de aprobación, sin duplicar en reimportaciones |

Secuencia obligatoria: 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11.
Las fases 05 a 10 son **cortes verticales**: cada una termina con backend y UI funcionando.
La fase 12 es una adición posterior (agregada fuera del orden original, ver §10): solo depende
de la fase 08 (necesita que exista `RegistroEjecucion`) y puede ejecutarse en cualquier momento
después de ella, sin bloquear ni ser bloqueada por 09, 10 u 11.

---

## 8. Definición de terminado (aplica a todas las fases)

Una fase está terminada cuando **todo** esto es cierto:

1. `docker compose up` levanta sin errores.
2. Backend: `pytest` en verde y `ruff check backend/` sin hallazgos.
3. `python manage.py makemigrations --check --dry-run` no detecta cambios pendientes.
4. Frontend: `npm run build` sin errores y `npm run lint` limpio.
5. Los endpoints nuevos aparecen en `/api/schema/swagger/`.
6. Los criterios de aceptación propios de la fase se cumplen y están marcados en su archivo.
7. La sección "Evidencia" del archivo de la fase tiene la salida real de los comandos.
8. Hay commit en la rama de la fase.

---

## 9. Prompt de arranque por fase

Para lanzar cada fase con Sonnet o Haiku, pega exactamente esto:

```
Lee PLAN.md, docs/modelo-datos.md y docs/api-contrato.md.
Luego ejecuta docs/plan/fase-NN-<nombre>.md completo, paso por paso, sin saltarte ninguno
y sin adelantar trabajo de fases posteriores.
Al terminar: corre los comandos de verificación de la fase, pega su salida en la sección
"Evidencia" de ese archivo, marca los criterios de aceptación cumplidos y haz commit en la
rama fase-NN-<nombre>. Si algo falla dos veces, detente y repórtalo con el log completo.
```

---

## 10. Fuera de alcance (v1)

No se construye en esta versión, aunque el modelo de datos lo deja posible: facturación a
clientes, integración con Azure DevOps, flujos de aprobación con varios niveles, notificaciones
por correo, multiempresa (tenancy), aplicación móvil, Gantt interactivo con arrastre (la fase 07
entrega un cronograma de solo lectura) e importación masiva desde Excel (la fase 10 solo
exporta).

> **Cambio de alcance (post-v1, fase 12):** la integración con Jira quedó excluida originalmente
> junto con Azure DevOps. Se agregó como fase 12 porque el usuario necesita las horas reales que
> ya se registran en Jira/Tempo sin duplicar la captura manual. El recorte sigue siendo mínimo:
> **solo importación unidireccional de horas (worklogs de Tempo → `RegistroEjecucion`)**, disparada
> a mano con un comando de gestión. Siguen fuera de alcance: cualquier sincronización en el otro
> sentido, importar tareas/issues de Jira como `Tarea` automáticamente, Azure DevOps, y cualquier
> disparo automático (programado o por webhook) — eso queda para una iteración posterior si hace
> falta.
