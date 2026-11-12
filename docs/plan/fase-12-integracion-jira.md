# Fase 12 — Importación de horas desde Jira/Tempo

**Rama:** `fase-12-integracion-jira` · **Depende de:** fase 08 · **Esfuerzo:** 1-2 sesiones

## Objetivo

Cubrir el objetivo 6 (ver `PLAN.md` §1 y §10): traer a `RegistroEjecucion` las horas reales que
los recursos ya registran en **Jira, usando el módulo Tempo Timesheets** (Jira Cloud), sin
reemplazar el registro manual que ya existe desde la fase 08 — ambos conviven. La importación es
**unidireccional** (Jira/Tempo → esta app) y se dispara a mano con un comando de gestión. El
proyecto de Jira se asocia desde un selector con la lista real de proyectos (no a mano), y si los
registros importados entran pendientes de aprobación o ya aprobados es un interruptor global que
solo `ADMIN` puede cambiar desde una pantalla de configuración.

## Precondiciones

- Fase 08 terminada (`RegistroEjecucion` con su ciclo de aprobación ya funcionando).
- Lee `docs/modelo-datos.md` §3 (`Proyecto.clave_jira`), §5 (`Tarea.clave_jira`), §6
  (`RegistroEjecucion.origen`/`id_externo`, `ConfiguracionImportacionJira` y la subsección
  "Integración de horas con Jira/Tempo"), y `PLAN.md` §10 (nota de cambio de alcance).
- **Credenciales necesarias antes de poder ejecutar y probar esta fase contra Jira real**
  (ver la sección "Qué se necesita" más abajo). Sin ellas se puede implementar y probar todo
  con mocks, pero no verificar contra el Jira/Tempo real.

---

## Qué se necesita para conectar (antes de ejecutar esta fase)

Jira Cloud y Tempo Cloud son sistemas separados con tokens separados:

1. **URL del sitio de Jira Cloud**, p. ej. `https://tuempresa.atlassian.net`. **Ojo:** no es
   `https://api.tempo.io` — esa es siempre la misma para todos los clientes de Tempo y ya la
   conoce el cliente; lo que hace falta aquí es la URL propia de tu instancia de Jira.
2. **Un token de API de Jira** + el correo de la cuenta dueña del token — se genera en
   `https://id.atlassian.com/manage-profile/security/api-tokens`. Se usa con Basic Auth
   (`correo:token`) contra `/rest/api/3/...` para listar proyectos, traducir `accountId` →
   correo y `issueId` → clave del issue (`PROY-123`). Basta con permisos de **lectura** sobre
   los proyectos involucrados.
3. **Un token de API de Tempo** — lo genera un administrador de Tempo desde
   *Jira → Apps → Tempo → Settings → API Integration → New Token*. Se usa como Bearer token
   contra `https://api.tempo.io/4/worklogs`. Basta con alcance de **lectura** de worklogs.
4. Opcional pero recomendado: confirmar que el **correo de cada `Recurso`** en esta app
   coincide con el correo de su cuenta de Jira (es la forma en que se resuelve el recurso).

Las cuatro credenciales (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `TEMPO_API_TOKEN`) se
guardan **solo** en `.env` (ya agregadas a `PLAN.md` §6 y a `.env.example`), nunca en el código
ni en el repositorio. La asociación de qué proyecto de Jira corresponde a cuál `Proyecto` de
esta app ya **no** requiere una lista previa: se elige desde un selector dentro del formulario
de proyecto, que trae la lista real de proyectos de Jira (12.2/12.5).

---

## Backend

### 12.1 Modelo y migraciones

1. `apps/core/choices.py`: nuevo `OrigenRegistro` (`MANUAL` \| `JIRA`); agregar `IMPORTACION` a
   `TipoEvento`.
2. `apps/ejecucion/models.py::RegistroEjecucion`: agregar `origen` (default `MANUAL`) e
   `id_externo` (Char(100), null). Constraint `UniqueConstraint(fields=["origen", "id_externo"],
   condition=Q(id_externo__isnull=False))`.
3. `apps/proyectos/models.py::Proyecto`: agregar `clave_jira` (Char(50), null, blank). Se llena
   eligiendo de la lista real de proyectos de Jira (12.2/12.5), nunca a mano.
4. `apps/tareas/models.py::Tarea`: agregar `clave_jira` (Char(30), null, blank, **unique**); este
   sí es texto libre (no hay selector de issues en esta fase, ver "Fuera de alcance").
5. `apps/ejecucion/models.py`: nuevo modelo singleton `ConfiguracionImportacionJira`
   (`auto_aprobar_importados` Boolean, default `False`) — interruptor global, ver
   `docs/modelo-datos.md` §6. Una sola fila; el servicio/la vista hacen `get_or_create(pk=1)`.
6. Migraciones para las tres apps (incluida la fila inicial de `ConfiguracionImportacionJira`
   vía migración de datos, para que `GET` nunca devuelva 404 por "no existe todavía").

### 12.2 Cliente de Jira/Tempo

7. `apps/ejecucion/integraciones/jira_tempo.py`: clase `ClienteJiraTempo` (usa `requests`, ya
   en `pyproject.toml` por el login con Google):
   - `__init__`: lee `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `TEMPO_API_TOKEN` de
     `settings` (que a su vez los lee de variables de entorno, mismo patrón que
     `GOOGLE_CLIENT_ID` en `config/settings/base.py`).
   - `listar_proyectos()`: `GET /rest/api/3/project/search` (paginado), devuelve
     `[{clave, nombre}]` — alimenta el selector del formulario de proyecto (12.5/12.7).
   - `obtener_worklogs(desde, hasta)`: pagina `GET https://api.tempo.io/4/worklogs` con
     `Authorization: Bearer <TEMPO_API_TOKEN>`.
   - `resolver_claves_issue(issue_ids)`: un solo `GET /rest/api/3/search?jql=id in (...)` con
     Basic Auth (`JIRA_EMAIL`:`JIRA_API_TOKEN`) para resolver muchos ids de una vez (no uno por
     uno).
   - `resolver_correo_usuario(account_id)`: `GET /rest/api/3/user?accountId=`, cacheado en
     memoria por `account_id` durante la corrida (no entre corridas).
   - Errores de red o HTTP: `ErrorIntegracionJira` propia, con el detalle (status + cuerpo) para
     que el comando o el endpoint lo reporten de forma legible, nunca como traceback crudo.

### 12.3 Servicio de importación

8. `apps/ejecucion/services.py` (o módulo nuevo en la misma app, a decidir al implementar):
   `importar_horas_jira(desde, hasta, *, dry_run=False)`:
   - obtiene los worklogs del rango; resuelve proyecto por el prefijo de la clave del issue
     contra `Proyecto.clave_jira`, tarea por `Tarea.clave_jira`, recurso por `Recurso.email`;
   - arma cada `RegistroEjecucion` con `periodicidad=DIARIA`,
     `periodo_inicio=periodo_fin=<fecha del worklog>`, reutilizando la misma función que ya
     congela `valor_hora_aplicado` con `valor_hora_vigente` en el alta manual;
   - reutiliza `validar_topes` (advertencia) y `validar_solapamiento` (bloqueo) **sin
     duplicarlas**: un worklog que choca con un registro manual existente se reporta como
     conflicto, no se fuerza;
   - upsert por `(origen=JIRA, id_externo=<id del worklog>)`: crea si no existe; si existe y
     sigue `ENVIADO` o `RECHAZADO`, actualiza horas/descripción; si ya está `APROBADO`, lo deja
     intacto (inmutable) y lo cuenta como "omitido, ya aprobado";
   - cada fila nueva entra en `ENVIADO` o en `APROBADO` según lea
     `ConfiguracionImportacionJira.auto_aprobar_importados` en ese momento (nunca en
     `BORRADOR`); si entra `APROBADO`, `aprobado_por` queda `null` (no la aprobó una persona);
   - `dry_run=True`: hace todo el cálculo y la validación pero no escribe nada;
   - devuelve `{creados, actualizados, omitidos: [...], errores: [...]}` (mismo espíritu que
     `carga_lote` de la fase 08);
   - al terminar, una `registrar_evento(tipo_evento="IMPORTACION", ...)` por cada proyecto
     afectado, con el resumen de esa corrida.

### 12.4 Comando de gestión

9. `apps/ejecucion/management/commands/importar_horas_jira.py`:
   - argumentos `--desde YYYY-MM-DD` y `--hasta YYYY-MM-DD` (obligatorios), `--dry-run`
     (opcional);
   - si falta alguna de las 4 variables de entorno, falla de entrada con un mensaje que dice
     exactamente cuáles;
   - imprime el resumen final igual que `verificar_consistencia`/`limpiar_datos_demo`.

### 12.5 API

10. Agregar `clave_jira` a los serializers de lectura/escritura de `Proyecto` y de `Tarea` (sin
    permisos nuevos: quien ya puede editar el proyecto/la tarea, edita este campo).
11. Agregar `origen` al serializer de lectura de `RegistroEjecucion` (de solo lectura; el de
    escritura ya lo rechazaría si alguien lo manda, igual que hace con `codigo` en otros
    serializers) y el filtro `origen` a `FiltroRegistroEjecucion`.
12. `GET /integraciones/jira/proyectos/` (solo `ADMIN`/`PMO`): llama a
    `ClienteJiraTempo.listar_proyectos()` y devuelve `[{clave, nombre}]`. Si el cliente falla
    (token inválido, Jira no responde), 502 con el detalle, no 500 genérico.
13. `/configuracion-importacion-jira/` (solo `ADMIN`): `GET`/`PATCH` sobre la única fila de
    `ConfiguracionImportacionJira`, sin `{id}` en la ruta (mismo patrón que cualquier "singleton"
    — ver cómo resolvió algo equivalente `apps/tablero` si aplica, si no, un
    `GenericAPIView` propio con `get_object()` fijo al único registro).

### 12.6 Pruebas

14. Cliente Jira/Tempo probado con **mocks de HTTP** (agregar `responses` a las dependencias de
    desarrollo y a `docs/STACK-LOCK.md`) — los tests nunca llaman a la red real.
15. `importar_horas_jira`:
    - un worklog nuevo crea un `RegistroEjecucion` `ENVIADO`, `origen=JIRA`, tarifa congelada
      (con `auto_aprobar_importados=False`, el default).
    - con `auto_aprobar_importados=True`, el worklog nuevo crea el registro directo en
      `APROBADO` con `aprobado_por=null`.
    - reimportar el mismo worklog actualiza el mismo registro, no duplica.
    - reimportar uno ya `APROBADO` lo deja intacto y lo reporta como omitido.
    - un worklog de un proyecto sin `clave_jira` mapeada se omite y se reporta por nombre.
    - un worklog de un autor sin `Recurso.email` coincidente se omite y se reporta.
    - un worklog que solapa con un registro manual se omite con el mismo 422 de
      `validar_solapamiento`, no se duplica la hora.
    - `--dry-run` no escribe nada en la base.
    - un token inválido o un error de red del cliente se reporta con mensaje claro.
16. `GET /integraciones/jira/proyectos/`: solo `ADMIN`/`PMO` (403 para los demás roles); un error
    del cliente Jira se traduce a 502 con detalle, no un 500 crudo.
17. `/configuracion-importacion-jira/`: solo `ADMIN` puede `PATCH` (403 para los demás); el valor
    persiste entre peticiones (no se resetea).

---

## Frontend

### 12.7 Pantallas

18. **Formulario de Proyecto**: reemplaza el campo de texto libre por un `app-select` "Proyecto
    en Jira" que trae sus opciones de `GET /integraciones/jira/proyectos/` (con opción "Ninguno"
    para dejarlo sin mapear); guarda la clave elegida en `Proyecto.clave_jira`.
19. **Formulario/edición de Tarea**: campo de texto libre opcional "Clave en Jira" (sin
    selector de issues en esta fase).
20. **Nueva pantalla mínima de administración** (p. ej. `/admin/integraciones` o una sección
    dentro de una pantalla de administración ya existente): un único interruptor
    "Aprobar automáticamente las horas importadas de Jira", que lee y escribe
    `/configuracion-importacion-jira/`. Visible y editable solo para `ADMIN`
    (`permisoGuard` análogo al de `/admin/roles`).
21. Donde se listan/aprueban registros de ejecución (bandeja de aprobaciones, mi registro de
    horas): un `app-badge` "Jira" en los registros con `origen=JIRA`, para que quien aprueba
    sepa que la fuente es externa.
22. Nada de botón "sincronizar ahora" ni disparo de la importación desde el frontend en esta
    fase (ver "Fuera de alcance") — el único disparo es el comando de gestión.

---

## Criterios de aceptación

- [x] `importar_horas_jira --desde --hasta` trae worklogs reales de Tempo como
      `RegistroEjecucion`, en `ENVIADO` o `APROBADO` según el interruptor global.
- [x] Reimportar el mismo rango de fechas no duplica registros.
- [x] Un registro ya `APROBADO` nunca se modifica al reimportar.
- [x] Los worklogs sin proyecto o recurso mapeado se reportan por nombre, no se pierden en
      silencio.
- [x] `--dry-run` no deja ningún rastro en la base.
- [x] El formulario de proyecto asocia la clave de Jira eligiéndola de una lista real, no
      escribiéndola a mano.
- [x] Solo `ADMIN` puede cambiar el interruptor de aprobación automática, desde una pantalla.
- [x] Las credenciales viven solo en variables de entorno, nunca en el código ni en el repo.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/ejecucion -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend ruff check .
docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
docker compose -f infra/docker-compose.yml exec backend python manage.py importar_horas_jira --desde 2026-01-01 --hasta 2026-01-31 --dry-run
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Sincronización en sentido contrario (esta app → Jira), importación automática/programada o por
webhook, selector de issues de Jira para `Tarea.clave_jira` (queda como texto libre), importar
issues de Jira como `Tarea` automáticamente, Azure DevOps, resolución automática de conflictos de
solapamiento (se reportan, no se resuelven solos), aprobación automática configurable **por
proyecto** (el interruptor es global, no por proyecto — ver la decisión documentada al crear esta
fase).

> **Adenda posterior**: el botón de "sincronizar ahora" estaba originalmente fuera de alcance
> (el disparo iba a ser solo el comando de gestión); el usuario pidió agregarlo después de probar
> la fase, dejando que decida las fechas y el modo de aprobación por corrida sin usar la
> terminal. Ver sección "Adenda: botón de importación" más abajo.

## Evidencia

### Backend

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/ejecucion -q
........................................................................ [ 74%]
.........................                                                [100%]
97 passed in 58.23s

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 49%]
........................................................................ [ 66%]
........................................................................ [ 82%]
........................................................................ [ 99%]
..                                                                       [100%]
434 passed in 280.39s

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
No changes detected

$ docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yml
(sin warnings/errores; exit 0)
```

### Frontend

```
$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
Linting "frontend"...
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npx ng build
Application bundle generation complete. [19.552 seconds]
(chunk nuevo: integraciones; además formulario, aprobaciones y mi-registro
crecieron con los campos/badges de esta fase)
```

### Verificación contra el Jira/Tempo real del usuario (no solo mocks)

Con las credenciales reales (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `TEMPO_API_TOKEN`
del `.env` del usuario) y `--dry-run` (sin escribir nada):

1. **Primer intento → 2 bugs reales encontrados y corregidos**, ninguno visible con mocks:
   - `resolver_claves_issue` hacía un `GET /rest/api/3/search?jql=id in (...)` con potencialmente
     cientos de ids en la URL → Jira respondió **414 (URI demasiado larga)**. Se corrigió a
     `POST` con el `jql` en el cuerpo JSON, en lotes de `TAMANO_LOTE_ISSUES=100`.
   - Corregido el 414, Jira respondió **410**: el endpoint clásico `/rest/api/3/search` ya no
     existe (`"La API solicitada se ha eliminado. Migra a /rest/api/3/search/jql"`). Se migró al
     nuevo endpoint, que pagina por `nextPageToken`/`isLast` en vez de `startAt`.
2. **Tras corregir ambos, una corrida real contra ~14 meses de worklogs** (`--desde 2025-09-01
   --hasta 2026-11-12`) procesó miles de worklogs reales sin ningún error de conexión, reportando
   cada proyecto de Jira no mapeado por su clave real (`HUC`, `TA`, `DBB`, `GVS`, `VAL`, `EAD`,
   `IQ`, …) — exactamente el comportamiento esperado, ya que ningún `Proyecto` del entorno de
   desarrollo tenía `clave_jira` configurada todavía.
3. **Prueba de punta a punta con datos reales**: se mapeó temporalmente un proyecto de desarrollo
   (`PRY-2026-004`) a la clave real `HUC` y se repitió la corrida en `--dry-run`:
   `Creados: 1, Actualizados: 0, Omitidos: 13844, Errores: 1` — confirma que, en cuanto hay un
   proyecto mapeado, el worklog de un autor cuyo correo coincide con un `Recurso` se resuelve,
   valida y arma correctamente como `RegistroEjecucion` (congelando tarifa, periodo, etc.), y que
   miles de omisiones (proyecto o recurso no mapeado) se manejan una por una sin interrumpir el
   lote. El mapeo de prueba se revirtió inmediatamente después (no queda en la base).
4. `GET /rest/api/3/project/search` (para el selector del formulario de proyecto) y la resolución
   de correos de usuario funcionaron sin cambios contra el Jira real.

### Decisiones y discrepancias documentadas

1. **Dos bugs de integración solo aparecen contra el sistema real, nunca con mocks**: el límite
   de longitud de URL de Jira (414) y la baja del endpoint `/rest/api/3/search` en favor de
   `/rest/api/3/search/jql` (410). Los mocks de los tests se actualizaron para reflejar el
   endpoint y el método (`POST`) correctos; quien reutilice este cliente contra otro tenant de
   Jira no debería toparse con ninguno de los dos.
2. **`ConfiguracionImportacionJira` no usa `ModeloBase`**: no tiene dueño ni borrado lógico, solo
   existe para una fila única (`pk=1` forzado en `save()`); se documentó así explícitamente en
   `docs/modelo-datos.md` §6 para que no se confunda con el resto de modelos del proyecto.
3. **`Tarea.clave_jira` sigue siendo texto libre** (sin selector de issues), a diferencia de
   `Proyecto.clave_jira` que si tiene selector — así quedó acotado en el alcance acordado con el
   usuario antes de ejecutar esta fase.
4. El respaldo manual de la base de datos (`infra/respaldar_bd.ps1`, de una sesión anterior) no
   se tocó ni se necesitó para esta fase: todas las pruebas contra el Jira real fueron de
   **solo lectura** (`--dry-run` o lectura directa), y el único cambio de datos real (el mapeo de
   prueba de `PRY-2026-004`) se revirtió en el mismo turno.

## Adenda: botón de importación en `/admin/integraciones`

Pedido por el usuario después de probar la fase: un botón que dispare la importación eligiendo
fechas y modo de aprobación, sin usar la terminal.

### Diseño

- `importar_horas_jira(desde, hasta, *, dry_run=False, auto_aprobar=None)` gana el parámetro
  `auto_aprobar`: si se indica explícito (`True`/`False`), decide la aprobación **solo para esa
  corrida**, sin tocar `ConfiguracionImportacionJira`; si se omite (`None`, el caso del comando de
  gestión), sigue usando el interruptor global, sin cambiar el comportamiento existente.
- `POST /integraciones/jira/importar/` (`ImportarHorasJiraView`, solo `ADMIN`): valida variables
  de entorno, fechas y `hasta >= desde` antes de llamar al servicio; devuelve el mismo resumen que
  el comando.
- `/admin/integraciones`: nueva tarjeta con fecha desde/hasta, un selector "¿Cómo deben entrar
  estas horas?" (pendientes de aprobación / aprobadas automáticamente — por defecto, el valor
  actual del interruptor global, pero editable solo para esa corrida), un interruptor "Solo
  simular" y el botón; muestra el resumen (creados, actualizados, omitidos, errores) al terminar.
  La tarjeta del interruptor global se mantiene aparte, aclarando que solo es el valor por
  defecto del comando de terminal.

### Evidencia

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/ejecucion -q
........................................................................ [ 66%]
....................................                                     [100%]
108 passed in 58.28s

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
(sin warnings/errores; exit 0)

$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npx ng build
Application bundle generation complete. [26.455 seconds]
```
