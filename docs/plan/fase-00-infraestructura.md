# Fase 00 — Infraestructura y andamiaje

**Rama:** `fase-00-infraestructura` · **Depende de:** nada · **Esfuerzo:** 1 sesión

## Objetivo

Dejar el repositorio con la estructura definitiva, Docker Compose levantando Postgres,
Django y Angular, y un endpoint de salud que responda. Ninguna lógica de negocio todavía.

## Precondiciones

- Docker Desktop corriendo en Windows.
- Node y npm disponibles en el host (para `ng new`), o usar el contenedor de Node.
- Puertos libres: 5432, 8000, 4200.

---

## Pasos

### 0.1 Repositorio

1. `git init` en `C:\proyectos\Seguimiento-pry` y crea la rama `fase-00-infraestructura`.
2. Crea `.gitignore` que excluya: `.env`, `__pycache__/`, `*.pyc`, `.pytest_cache/`,
   `.ruff_cache/`, `node_modules/`, `dist/`, `.angular/`, `media/`, `staticfiles/`, `*.sqlite3`,
   `.vscode/`, `coverage/`, `htmlcov/`.
3. Copia el bloque de variables de `PLAN.md` §6 a `.env.example` y crea tu `.env` local a
   partir de él, con una `DJANGO_SECRET_KEY` generada.

### 0.2 Backend Django

4. Crea `backend/pyproject.toml` con estas dependencias (fija las versiones a la última
   estable de cada una en el momento de instalar y anótalas en `docs/STACK-LOCK.md`):

   ```
   django, djangorestframework, djangorestframework-simplejwt,
   django-filter, django-cors-headers, drf-spectacular, django-environ,
   psycopg[binary], google-auth, requests, gunicorn,
   # dev
   pytest, pytest-django, pytest-cov, factory-boy, ruff
   ```

   En el mismo archivo configura `[tool.ruff]` (`line-length = 100`, reglas `E,F,I,UP,B,DJ`)
   y `[tool.pytest.ini_options]` (`DJANGO_SETTINGS_MODULE = "config.settings.test"`,
   `python_files = "test_*.py"`).

5. `django-admin startproject config backend` ajustado a la estructura de `PLAN.md` §3:
   `backend/manage.py` y `backend/config/`.

6. Divide la configuración en `config/settings/`:
   - `base.py`: lee todo con `environ.Env()`; `INSTALLED_APPS` con `rest_framework`,
     `rest_framework_simplejwt.token_blacklist`, `django_filters`, `corsheaders`,
     `drf_spectacular` y los `apps.*` que se irán creando; `AUTH_USER_MODEL = "accounts.Usuario"`
     (el modelo llega en la fase 01, deja la línea comentada con un `TODO fase-01`);
     `TIME_ZONE`, `LANGUAGE_CODE = "es-co"`, `USE_TZ = True`;
     `REST_FRAMEWORK` con `DEFAULT_AUTHENTICATION_CLASSES` de JWT,
     `DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`,
     `DEFAULT_PAGINATION_CLASS` propia, `PAGE_SIZE = 25`,
     `DEFAULT_SCHEMA_CLASS` de spectacular, `EXCEPTION_HANDLER` apuntando a
     `apps.core.exceptions.manejador_excepciones` (se implementa en la fase 02).
   - `dev.py`: `DEBUG=True`, CORS desde `.env`, `django-extensions` no se usa.
   - `prod.py`: `DEBUG=False`, `SECURE_*` activos, `ALLOWED_HOSTS` desde `.env`, `WhiteNoise`
     para estáticos.
   - `test.py`: hereda de `base`, base de datos en Postgres de pruebas, hashing de clave rápido.

7. Crea los diez paquetes de `backend/apps/` (`core`, `accounts`, `catalogos`, `recursos`,
   `proyectos`, `tareas`, `ejecucion`, `seguimiento`, `expediente`, `tablero`), cada uno con
   `__init__.py`, `apps.py` (con `name = "apps.<x>"`), `models.py`, `admin.py`, `serializers.py`,
   `views.py`, `urls.py`, `filters.py`, `services.py` y `tests/__init__.py`. Los archivos van
   vacíos salvo `apps.py`.

8. `apps/core/views.py`: vista `SaludView` pública que devuelve
   `{"estado": "ok", "version": "0.1.0", "base_datos": "ok"|"error", "hora": <ISO>}`
   comprobando la conexión con `connection.ensure_connection()`.

9. `config/urls.py`: incluye `path("api/v1/salud/", SaludView.as_view())`,
   `path("api/v1/", include(...))` para las apps, el admin en `/admin/` y las tres rutas de
   `drf-spectacular` de `docs/api-contrato.md` §10.

### 0.3 Frontend Angular

10. `ng new frontend --routing --style=css --ssr=false --standalone` (si la versión instalada
    ya hace standalone por defecto, omite la bandera). Prefijo de componentes: `app`.
11. Instala y configura **Tailwind 3.4**: `npm i -D tailwindcss@3 postcss autoprefixer`,
    `npx tailwindcss init`, `content: ["./src/**/*.{html,ts}"]`, y las tres directivas
    `@tailwind` en `src/styles.css`.
12. En `tailwind.config.js` define los tokens del panel bajo `theme.extend`:
    - `colors.marca` (escala 50–900), `colors.exito`, `colors.alerta`, `colors.peligro`,
      `colors.neutro` (escala), y los tres del semáforo: `semaforo.verde|amarillo|rojo`.
    - `borderRadius.panel`, `boxShadow.tarjeta`, `fontFamily.sans` con una pila con respaldo.
    Los componentes de la fase 04 solo usan estos tokens.
13. Crea las carpetas vacías de `src/app/` según `PLAN.md` §3 con un `.gitkeep`.
14. `src/environments/environment.ts` y `environment.development.ts` con
    `apiBaseUrl` apuntando a `http://localhost:8000/api/v1`.
15. En `package.json` deja los scripts: `start`, `build`, `test`, `lint`
    (instala `@angular-eslint` si `ng lint` no está configurado).
16. Reemplaza el componente raíz por un `AppComponent` mínimo que muestre el resultado de
    `GET /salud/`, para probar la conexión de punta a punta. Esta pantalla se elimina en la fase 04.

### 0.4 Docker

17. `infra/backend.Dockerfile`: base `python:3.12-slim`, instala dependencias del sistema
    (`build-essential`, `libpq-dev`), copia `pyproject.toml`, instala, copia el código,
    expone 8000, comando `python manage.py runserver 0.0.0.0:8000`.
18. `infra/frontend.Dockerfile`: base `node:22-alpine`, instala dependencias, expone 4200,
    comando `npm start -- --host 0.0.0.0 --poll 2000`.
19. `infra/docker-compose.yml` con tres servicios:
    - `db`: `postgres:16-alpine`, variables desde `.env`, volumen `datos_pg`,
      `healthcheck` con `pg_isready`, puerto 5432.
    - `backend`: construido con `backend.Dockerfile`, `depends_on: db (service_healthy)`,
      monta `./backend:/app` y `./media:/app/media`, puerto 8000.
    - `frontend`: construido con `frontend.Dockerfile`, monta `./frontend:/app` y un volumen
      anónimo para `node_modules`, puerto 4200.
20. `infra/docker-compose.override.yml` con lo específico de desarrollo (recarga en caliente,
    `stdin_open`, `tty`).
21. Deja un `Makefile` o `scripts/dev.ps1` con los atajos: `up`, `down`, `logs`, `migrate`,
    `shell`, `test`, `seed`. En Windows el script de PowerShell es el principal.

### 0.5 Documentación

22. `README.md`: requisitos, cómo copiar `.env.example`, `docker compose -f infra/docker-compose.yml up`,
    URLs (`http://localhost:4200`, `http://localhost:8000/api/v1/salud/`,
    `http://localhost:8000/api/schema/swagger/`), y cómo correr pruebas y lint.
23. `docs/STACK-LOCK.md`: tabla con las versiones **reales** instaladas, obtenidas de
    `python -V`, `pip list`, `node -v`, `ng version`, `npx tailwindcss -v`,
    `docker exec ... postgres -V`.

---

## Criterios de aceptación

- [x] `docker compose -f infra/docker-compose.yml up` levanta los tres servicios sin error.
- [x] `GET http://localhost:8000/api/v1/salud/` devuelve 200 con `base_datos: "ok"`.
- [x] `http://localhost:4200` carga y muestra el estado que devuelve `/salud/` (verificado vía
      curl y logs del contenedor; en este entorno no hay navegador disponible para captura visual).
- [x] `http://localhost:8000/api/schema/swagger/` abre sin errores.
- [x] `ruff check backend/` sin hallazgos y `pytest` corre (aunque sea con 0 pruebas).
- [x] `cd frontend && npm run build` termina sin errores.
- [x] `docs/STACK-LOCK.md` tiene versiones reales, no supuestas.
- [x] `.env` **no** está en el control de versiones.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml up -d
curl -s http://localhost:8000/api/v1/salud/
docker compose -f infra/docker-compose.yml exec backend ruff check .
docker compose -f infra/docker-compose.yml exec backend pytest -q
cd frontend && npm run build && npm run lint
```

## Fuera de alcance de esta fase

Modelos, migraciones de negocio, autenticación real, componentes de UI, estilos del panel.

## Evidencia

Nota de entorno: no hay navegador disponible en esta sesión para captura visual de
`http://localhost:4200`; la verificación de esa URL se hizo con `curl`, con los logs del
contenedor `frontend` (build sin errores, bundle servido) y comprobando que la cabecera
`Access-Control-Allow-Origin` autoriza ese origen contra `/salud/`.

```
$ docker compose -f infra/docker-compose.yml up -d
 Network infra_default  Created
 Volume infra_datos_pg  Created
 Volume infra_node_modules  Created
 Container infra-db-1  Started
 Container infra-db-1  Healthy
 Container infra-backend-1  Started
 Container infra-frontend-1  Started

$ docker compose -f infra/docker-compose.yml ps
NAME               IMAGE                COMMAND                  SERVICE    STATUS
infra-backend-1    infra-backend        "python manage.py ru…"   backend    Up (healthy db dependency met)
infra-db-1         postgres:16-alpine   "docker-entrypoint.s…"   db         Up (healthy)
infra-frontend-1   infra-frontend       "docker-entrypoint.s…"   frontend   Up

$ curl -s -w "\nHTTP:%{http_code}\n" http://localhost:8000/api/v1/salud/
{"estado":"ok","version":"0.1.0","base_datos":"ok","hora":"2026-10-30T21:29:08.774234+00:00"}
HTTP:200

$ curl -s -i -H "Origin: http://localhost:4200" http://localhost:8000/api/v1/salud/
HTTP/1.1 200 OK
access-control-allow-origin: http://localhost:4200
...
{"estado":"ok","version":"0.1.0","base_datos":"ok","hora":"..."}

$ curl -s -o /dev/null -w "swagger HTTP:%{http_code}\n" http://localhost:8000/api/schema/swagger/
swagger HTTP:200
$ curl -s -o /dev/null -w "schema HTTP:%{http_code}\n" http://localhost:8000/api/schema/
schema HTTP:200
$ curl -s -o /dev/null -w "redoc HTTP:%{http_code}\n" http://localhost:8000/api/schema/redoc/
redoc HTTP:200

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
no tests ran in 1.01s
(exit code 5: sin pruebas recolectadas, esperado en esta fase)

$ docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
No changes detected

$ docker compose -f infra/docker-compose.yml exec backend python manage.py check
System check identified no issues (0 silenced).

$ docker compose -f infra/docker-compose.yml exec backend python manage.py migrate
Applying contenttypes.0001_initial... OK
... (30 migraciones de admin, auth, contenttypes, sessions, token_blacklist) ... OK

$ docker compose -f infra/docker-compose.yml exec frontend npm run build
Application bundle generation complete. [5.271 seconds]
Initial total | 219.01 kB | 59.72 kB
Output location: /app/dist/frontend

$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
Linting "frontend"...
All files pass linting.

$ git status --short | head
?? .env.example
?? .gitignore
?? PLAN.md
?? README.md
?? backend/
?? docs/
?? frontend/
?? infra/
?? scripts/
(.env no aparece: está excluido por .gitignore)
```

Versiones reales quedaron registradas en [docs/STACK-LOCK.md](../STACK-LOCK.md).
