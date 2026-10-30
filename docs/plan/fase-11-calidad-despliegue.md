# Fase 11 — Calidad, pruebas y despliegue

**Rama:** `fase-11-calidad-despliegue` · **Depende de:** fase 10 · **Esfuerzo:** 1–2 sesiones

## Objetivo

Cerrar la versión 1: elevar la cobertura, probar de punta a punta el flujo crítico, revisar
seguridad, dejar la imagen de producción lista y documentar la operación.

## Precondiciones

- Fase 10 terminada y toda la funcionalidad operando con `seed_demo`.

---

## Pasos

### 11.1 Pruebas de backend

1. Mide la cobertura: `pytest --cov=apps --cov-report=term-missing --cov-report=html`.
   Meta: **≥70% global** y **≥90%** en estos módulos, que son los que tienen el dinero:
   `apps/tablero/services.py`, `apps/ejecucion/services.py`, `apps/recursos/services.py`,
   `apps/core/periodos.py`, `apps/core/calculos.py`, `apps/proyectos/services.py`.
2. Añade las pruebas que falten priorizando por riesgo, en este orden:
   fórmulas de control → solapamiento de periodos → tarifas vigentes → permisos por rol →
   transiciones de estado → carga de archivos.
3. Prueba de **concurrencia** en la generación de códigos: dos creaciones simultáneas de
   proyecto y de tarea no producen códigos duplicados (usa transacciones en hilos o
   `pytest-django` con `TransactionTestCase`).
4. Prueba de **integridad de los derivados**: un comando `verificar_consistencia` que
   recalcula `Tarea.horas_ejecutadas`, `RubroPresupuesto.monto_ejecutado` y
   `AsignacionRecurso.costo_planeado` desde cero y reporta diferencias. La prueba corre el
   comando tras `seed_demo` y exige cero diferencias. Este comando también sirve en operación.
5. `pytest --cov` queda configurado con `fail_under = 70` en `pyproject.toml`, para que la
   cobertura no se degrade en silencio.

### 11.2 Pruebas de frontend

6. Pruebas unitarias de los servicios de datos y de los componentes con lógica
   (`app-tabla`, `grafico`, la cuadrícula de captura de horas, el editor de seguimiento).
7. **End-to-end con Playwright** (`frontend/e2e/`), un solo recorrido que cubre el flujo
   crítico completo contra el entorno de Docker con `seed_demo`:
   1. login con usuario y contraseña;
   2. crear un proyecto con presupuesto en horas y dinero;
   3. agregar dos fases con pesos que sumen 100 y un hito;
   4. crear un recurso con tarifa y asignarlo al proyecto;
   5. pasar el proyecto a `EJECUCION`;
   6. crear una tarea y, con el proyecto ya en ejecución, otra con su motivo;
   7. registrar horas semanales como recurso y enviarlas;
   8. aprobarlas como líder;
   9. precargar y publicar un seguimiento;
   10. subir un documento al expediente y descargarlo;
   11. verificar en el tablero que el proyecto aparece con sus porcentajes correctos.
   El recorrido debe poder correrse varias veces (usa códigos con marca de tiempo).
8. Script `npm run e2e` y un `docker-compose.e2e.yml` que levante el entorno con una base
   limpia y `seed_demo` aplicado.

### 11.3 Revisión de seguridad

9. Lista de verificación, cada punto con su prueba o su evidencia:
   - [ ] `DEBUG=False` en producción y `DJANGO_SECRET_KEY` fuera del código.
   - [ ] `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` explícitos, sin `*`.
   - [ ] `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
         `SECURE_HSTS_SECONDS`, `X_FRAME_OPTIONS=DENY` activos en `prod.py`.
   - [ ] `python manage.py check --deploy` sin advertencias críticas.
   - [ ] Los `MEDIA` no se sirven como estáticos; toda descarga pasa por el endpoint con permiso.
   - [ ] Validación de extensión, tamaño y nombre de archivo en el servidor (no solo cliente).
   - [ ] Límite de intentos de login activo y probado.
   - [ ] Ningún endpoint de negocio con `AllowAny` (revisa uno por uno en el esquema OpenAPI).
   - [ ] Los listados filtran por rol (ya probado en la fase 03; vuelve a correr esas pruebas).
   - [ ] El detalle de un objeto fuera de alcance devuelve 404, no 403.
   - [ ] Nunca se devuelven trazas al cliente; el 500 solo lleva `traza_id`.
   - [ ] Los tokens no se registran en los logs; revisa el formateo de logs.
   - [ ] `pip list --outdated` revisado y las dependencias con vulnerabilidades conocidas
         actualizadas (`pip-audit` y `npm audit --omit=dev`).
10. Opcional, si el usuario lo pide: ejecuta `/security-review` sobre la rama antes de cerrar.

### 11.4 Rendimiento

11. Con `seed_demo` ampliado a 50 proyectos, 500 tareas y 5.000 registros de ejecución
    (`seed_demo --volumen=grande`), mide y deja registrado en `docs/rendimiento.md`:
    - `/tablero/resumen/`, `/tablero/proyectos/`, `/proyectos/`, `/tareas/`,
      `/registros-ejecucion/` y `/proyectos/{id}/cronograma/`.
    - Objetivo: p95 por debajo de 800 ms en local y número de consultas constante
      (no proporcional al número de filas).
12. Corrige con `select_related`, `prefetch_related`, `only()` e índices adicionales si hace
    falta. Si añades un índice, actualiza `docs/modelo-datos.md` §11.

### 11.5 Despliegue

13. `infra/docker-compose.prod.yml`:
    - `backend` con `gunicorn config.wsgi:application --workers 3 --timeout 60`,
      `DJANGO_SETTINGS_MODULE=config.settings.prod`, `collectstatic` en el arranque;
    - `frontend` construido (`npm run build`) y servido por `nginx:alpine` con la
      configuración de `infra/nginx/default.conf`: compresión gzip, caché de activos con hash,
      `try_files $uri /index.html` para las rutas de Angular, y `proxy_pass` de `/api/` y
      `/media/` hacia el backend;
    - `db` con volumen nombrado y sin puerto expuesto al host;
    - un servicio `migraciones` de un solo uso que corre `migrate` antes del backend.
14. Dockerfiles multietapa: el del frontend compila en Node y copia `dist/` a Nginx; el del
    backend usa una etapa de construcción para las dependencias y una final sin herramientas de
    compilación. El contenedor no corre como root.
15. `scripts/respaldo.ps1` y `scripts/restaurar.ps1` con `pg_dump` y `pg_restore`, y la
    instrucción en el README de probar la restauración al menos una vez (un respaldo que nunca
    se ha restaurado no es un respaldo).
16. **Integración continua** en `.github/workflows/ci.yml` (si el repositorio va a GitHub):
    servicio de Postgres, `ruff check`, `pytest --cov` con el `fail_under`,
    `npm ci && npm run lint && npm run build`, y el e2e en las ramas principales.

### 11.6 Documentación de cierre

17. `README.md` completo: requisitos, puesta en marcha en desarrollo, variables de entorno,
    cómo crear el superusuario, cómo cargar datos de demostración, cómo correr pruebas y lint,
    despliegue en producción, respaldo y restauración, y solución de problemas frecuentes.
18. `docs/manual-usuario.md`: guía breve por rol, con el flujo de trabajo típico
    (el PMO crea el proyecto y el presupuesto → el líder asigna recursos y crea tareas → el
    recurso registra horas → el líder aprueba → el líder publica el seguimiento → la dirección
    mira el tablero). Incluye qué significa cada color del semáforo y cómo se calcula.
19. `docs/operacion.md`: comandos de gestión disponibles (`seed_demo`, `seed_roles`,
    `recalcular_semaforos`, `actualizar_compromisos`, `verificar_consistencia`), cada cuánto
    conviene correrlos y qué hacer si uno reporta diferencias.
20. `CHANGELOG.md` con la versión 1.0.0 y el alcance entregado.
21. Actualiza `PLAN.md`: marca las fases terminadas y mueve a una sección "Pendiente para v2"
    lo que quedó fuera, con lo aprendido durante la ejecución.

---

## Criterios de aceptación

- [ ] Cobertura global ≥70% y ≥90% en los seis módulos críticos listados.
- [ ] `pytest` falla si la cobertura baja del umbral.
- [ ] `verificar_consistencia` reporta cero diferencias tras `seed_demo`.
- [ ] El recorrido e2e completo pasa dos veces seguidas sin intervención manual.
- [ ] `python manage.py check --deploy` sin advertencias críticas.
- [ ] Toda la lista de verificación de seguridad está marcada con su evidencia.
- [ ] `docs/rendimiento.md` tiene mediciones reales con el volumen grande.
- [ ] `docker compose -f infra/docker-compose.prod.yml up` sirve la aplicación compilada en
      un solo puerto, con la API accesible por el mismo origen.
- [ ] Un respaldo restaurado en una base vacía deja la aplicación funcionando.
- [ ] README, manual de usuario y documento de operación están completos.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest --cov=apps --cov-report=term-missing
docker compose -f infra/docker-compose.yml exec backend python manage.py verificar_consistencia
docker compose -f infra/docker-compose.yml exec backend python manage.py check --deploy
cd frontend && npm run lint && npm run build && npm run e2e
docker compose -f infra/docker-compose.prod.yml up -d --build
curl -s -o /dev/null -w "%{http_code}" http://localhost/
```

## Fuera de alcance de esta fase

Todo lo listado en `PLAN.md` §10. Si el usuario quiere alguno de esos puntos, se planifica
como fase 12 y siguientes, con su propio archivo.

## Evidencia

<!-- Pega aquí la salida real de los comandos de verificación. -->
