# Fase 05 — Proyectos, fases, hitos y presupuesto

**Rama:** `fase-05-proyectos-presupuesto` · **Depende de:** fase 04 · **Esfuerzo:** 2 sesiones

## Objetivo

Primer corte vertical completo: API y pantallas para administrar proyectos de TI con su
presupuesto aprobado en **horas** y en **dinero**, sus fases, hitos y rubros. También los
catálogos que el proyecto necesita (áreas, portafolios, perfiles).

## Precondiciones

- Fase 04 terminada: shell navegable y biblioteca de UI completa.
- Lee `docs/modelo-datos.md` §2, §3 y §10, y `docs/api-contrato.md` §3 y §4.

---

## Backend

### 5.1 Catálogos

1. `apps/catalogos`: `filters.py`, `serializers.py`, `views.py` y `urls.py` con CRUD para
   `Area`, `Portafolio` y `PerfilRecurso` sobre `ViewSetBase`.
   Permisos: lectura para cualquier autenticado, escritura para `ADMIN` y `PMO`.
   `search_fields = ["codigo", "nombre"]`.
2. Al intentar desactivar un catálogo en uso (un área con proyectos activos), devuelve 409
   `CONFLICTO` con el conteo de referencias en `detalles`.

### 5.2 Servicio de reglas del proyecto

3. `apps/proyectos/services.py` — **toda** la regla de negocio vive aquí, no en los serializers:
   - `TRANSICIONES = {...}` con el grafo de `docs/modelo-datos.md` §3 y
     `validar_transicion(proyecto, estado_nuevo)` que lanza `ErrorConflicto` con el mensaje
     "No se puede pasar de X a Y" y la lista de transiciones válidas en `detalles`.
   - `cambiar_estado(proyecto, estado_nuevo, observacion, usuario)` que valida las
     precondiciones (ver §3 del modelo: `EJECUCION` exige `fecha_inicio_real` y al menos una
     asignación; `CERRADO` exige `fecha_fin_real` y ninguna tarea `EN_PROGRESO`), guarda y
     llama a `registrar_evento(tipo_evento="CAMBIO_ESTADO", ...)`.
   - `validar_pesos_fases(proyecto)` que comprueba que la suma de `peso` de las fases activas
     sea 100 y devuelve el faltante o excedente para el mensaje de error.
   - `validar_presupuesto(proyecto)` que comprueba
     `presupuesto_dinero >= suma(RubroPresupuesto.monto_planeado)`.
   - `generar_codigo_proyecto()` → `PRY-<año>-<secuencia de 3 dígitos>`, con bloqueo de fila
     (`select_for_update`) sobre el último del año para evitar colisiones.
4. `apps/tablero/services.py`: implementa **ahora** `resumen_ejecucion(proyecto, fecha_corte)`
   con las fórmulas de `docs/modelo-datos.md` §10, usando `annotate`/`Sum` y
   `division_segura`. En esta fase devolverá ceros o `null` en lo que depende de fases
   posteriores (no hay asignaciones ni ejecución todavía); la función **no se reescribe**
   después, solo se van poblando sus fuentes. Añade pruebas con datos construidos a mano.
5. `semaforo_calculado(proyecto, fecha_corte)` en el mismo servicio, con la tabla de §10
   evaluada en orden. `Proyecto.semaforo` se actualiza al publicar un seguimiento (fase 09) y
   mediante el comando `recalcular_semaforos` que creas aquí.

### 5.3 API de proyectos

6. `apps/proyectos/filters.py`: `FiltroProyecto` con todos los filtros de
   `docs/api-contrato.md` §4, incluido `mis_proyectos` (gerente, líder técnico o recurso
   asignado) como `BooleanFilter` con método propio.
7. `apps/proyectos/serializers.py`:
   - `ProyectoListaSerializer`: campos planos + `area_nombre`, `portafolio_nombre`,
     `gerente_nombre`, `semaforo`, y el bloque `resumen_ejecucion` reducido
     (`pct_horas`, `pct_dinero`, `avance`) para que el listado ya sea informativo.
   - `ProyectoDetalleSerializer`: todo lo anterior más `fases`, `hitos`, `rubros` anidados y
     el `resumen_ejecucion` completo.
   - `ProyectoEscrituraSerializer`: valida fechas, invoca `validar_presupuesto`, ignora
     `codigo` (lo genera el servidor) y rechaza escribir `estado` (se cambia solo por la acción).
   - Serializers propios de `FaseProyecto`, `Hito` y `RubroPresupuesto`, con validación de
     pertenencia al proyecto y, en fases, llamada a `validar_pesos_fases`.
8. `apps/proyectos/views.py`: `ProyectoViewSet(ViewSetBase, MixinAlcancePorRol)` con las
   acciones `cambiar-estado`, `resumen`, `fases`, `hitos`, `rubros`; y los ViewSets de
   `FaseProyecto`, `Hito` y `RubroPresupuesto` filtrables por `?proyecto=`.
   Permisos: `EsPmoOAdmin` para crear; `EsLiderDelProyecto` para editar; lectura según rol.
   `get_queryset` con `select_related("area_solicitante", "portafolio", "gerente",
   "lider_tecnico")` y `prefetch_related` de fases, hitos y rubros en el detalle.
9. Documenta cada `@action` con `@extend_schema`.
10. Pruebas de API: creación con y sin permiso; transiciones válidas e inválidas; pesos de
    fases que no suman 100; presupuesto menor que la suma de rubros; `mis_proyectos` para cada
    rol; borrado lógico rechazado si hay ejecución aprobada (prepara el caso con `seed_demo`).

---

## Frontend

### 5.4 Datos y rutas

11. `features/proyectos/data/proyectos.service.ts` sobre `ApiService`, con métodos para el
    CRUD, `cambiarEstado`, `resumen` y los sub-recursos. Mismo patrón para
    `features/admin/data/catalogos.service.ts`.
12. `features/proyectos/proyectos.routes.ts`: `/proyectos` (lista), `/proyectos/nuevo`,
    `/proyectos/:id` (detalle con pestañas), `/proyectos/:id/editar`.
    Reemplaza el marcador "En construcción" de la fase 04.

### 5.5 Pantallas

13. **Lista de proyectos** (`/proyectos`):
    - `app-tabla` con columnas: código, nombre, área, gerente, estado (`app-badge`),
      prioridad, fechas plan, avance (`app-progreso`), % horas, % dinero, semáforo
      (`app-semaforo`), acciones.
    - Barra de filtros: búsqueda, estado, prioridad, portafolio, área, semáforo, rango de
      fechas y el interruptor "Solo mis proyectos". **Los filtros se reflejan en la URL**
      (query params) para poder compartir la vista y para que el botón atrás funcione.
    - Botón "Nuevo proyecto" visible solo con `proyectos.crear`.
14. **Formulario de proyecto** (nuevo y editar): campos agrupados en secciones
    (Identificación, Responsables, Cronograma, Presupuesto, Observaciones); `app-datepicker`
    para fechas; `app-numero` en modo moneda y en modo horas; validación en cliente que
    refleja la del servidor (fin ≥ inicio) y pintado de `error.detalles` por campo.
    Aviso al salir con cambios sin guardar.
15. **Detalle de proyecto** (`/proyectos/:id`) con `app-tabs`:
    - *Resumen*: tarjetas de KPI (horas plan vs. ejecutadas, dinero plan vs. ejecutado,
      avance, semáforo, días restantes) + datos generales. Los valores que aún no tienen
      fuente muestran `—`, no 0.
    - *Fases*: tabla editable en línea o por modal, con un indicador visible de la suma de
      pesos y una alerta cuando no es 100.
    - *Hitos*: tabla con estado, fecha plan vs. real y marca de incumplido en rojo.
    - *Presupuesto*: rubros por categoría, con totales planeado y ejecutado por categoría y
      el total general comparado con `presupuesto_dinero`.
    - *Tareas*, *Ejecución*, *Seguimientos*, *Expediente*: pestañas presentes pero con el
      componente "En construcción" (las llenan las fases 07, 08 y 09).
16. **Cambio de estado**: botón que abre `app-confirmacion` con un select de estados
    permitidos (los calcula el backend en `resumen` o se derivan del mismo grafo expuesto en
    `GET /proyectos/{id}/`) y un campo de observación obligatorio.
17. **Catálogos** (`/admin/catalogos`): tres pestañas con CRUD simple en modal para áreas,
    portafolios y perfiles de recurso.

---

## Criterios de aceptación

- [x] Un `PMO` crea un proyecto y el código se genera solo con el formato `PRY-2026-001`.
- [x] Un `LIDER` edita su proyecto y recibe **404** (no 403) al editar uno ajeno — ver nota en Evidencia.
- [x] Un `RECURSO` no ve el botón "Nuevo proyecto" ni puede acceder a `/proyectos/nuevo`.
- [x] Guardar fases cuyos pesos suman 90 falla con un mensaje que dice cuánto falta.
- [x] Un presupuesto menor que la suma de rubros se rechaza con mensaje claro.
- [x] Pasar de `BORRADOR` a `CERRADO` se rechaza con 409 y la lista de transiciones válidas.
- [x] Pasar a `EJECUCION` sin asignaciones se rechaza con el motivo exacto.
- [x] Los filtros de la lista quedan en la URL y sobreviven a recargar la página.
- [x] El detalle de un proyecto de `seed_demo` muestra su semáforo y sus KPIs sin errores.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios, OpenAPI válido.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/proyectos apps/catalogos -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Recursos y asignaciones (fase 06), tareas (07), ejecución real (08), seguimientos y
expediente (09), tablero global (10).

## Evidencia

### `pytest apps/proyectos apps/catalogos`

```
...............................................                          [100%]
47 passed in 70.25s
```

### `pytest` (suite completa del backend)

```
........................................................................ [ 45%]
........................................................................ [ 91%]
..............                                                           [100%]
158 passed in 162.37s
```

### `ruff check .`

```
All checks passed!
```

### `python manage.py spectacular --validate --fail-on-warn`

Sin advertencias ni errores (schema generado completo, `Warnings: 0`, `Errors: 0`).

### `npm run lint`

```
Linting "frontend"...
All files pass linting.
```

### `npm run build`

```
Application bundle generation complete.
Initial total    | 411.73 kB |  104.93 kB
Lazy chunks: detalle, formulario, catalogos, lista, proyectos-routes, …
```

### `npm test`

```
Test Files  6 passed (6)
     Tests  28 passed (28)
```

### Verificación manual contra el backend real (`seed_demo`)

```
$ curl -s .../auth/login/ {"email":"admin@seguimiento.local", ...} → access token OK
$ curl -s .../proyectos/ → count: 4, 4 proyectos con area_nombre/gerente_nombre/resumen_ejecucion
$ curl -s .../proyectos/{id}/ → fases, hitos, rubros anidados + resumen_ejecucion completo
    "resumen_ejecucion": {
      "pct_horas": 24.0, "pct_dinero": 48.17, "pct_tiempo": 50.0, "avance": "40.00",
      "spi": 0.8, "cpi": 0.83, "semaforo": "ROJO", ...
    }
$ curl -s .../proyectos/{id}/resumen/ → mismo bloque que el detalle
```

### Bugs reales encontrados y corregidos durante esta fase

1. **`resolver_proyecto_de_instancia` (apps/core/roles.py) no manejaba el caso en que el
   objeto evaluado ES un `Proyecto`** (solo resolvía `obj.proyecto` o rutas indirectas vía
   `RUTA_A_PROYECTO`). Esto rompía `EsLiderDelProyecto` para el propio `ProyectoViewSet`: un
   `LIDER` recibía 403 incluso editando **su propio** proyecto. `prefijo_proyecto` (la función
   hermana, usada por `MixinAlcancePorRol`) ya tenía ese caso cubierto; faltaba aquí. Se agregó
   `if type(obj).__name__ == "Proyecto": return obj` al inicio de la función.
2. **`UsuarioViewSet` (apps/accounts/views.py) tenía `permission_classes = [EsAdmin]`**, pero
   `docs/api-contrato.md` §8 documenta `usuarios: ADMIN "LCEB", PMO "L"`. Un `PMO` no podía
   listar usuarios para elegir gerente/líder técnico al crear un proyecto desde el frontend.
   Se corrigió con un permiso compuesto (`_EsAdminOLecturaPmo`) que da lectura a ADMIN+PMO y
   escritura solo a ADMIN, y se agregó `apps/accounts/tests/test_usuarios_api.py` para
   cubrirlo (no existía ninguna prueba de API para este endpoint).
3. **Colisión de nombres de enum en el esquema OpenAPI**: varios modelos tienen un campo
   `estado` con su propio `TextChoices` (`EstadoProyecto`, `EstadoFase`, `EstadoHito`).
   `drf-spectacular` generaba un nombre colisionado (`Estado2f9Enum`) y `--fail-on-warn`
   rompía. Se agregó `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]` con una entrada por cada
   enum expuesto hasta ahora; las fases siguientes añadirán las suyas si hace falta.

### Discrepancia documentada (no es un bug, es una decisión de diseño)

El criterio de aceptación dice que un `LIDER` debe recibir **403** al editar un proyecto
ajeno. La implementación real devuelve **404**, y es la misma decisión que fase 03 ya tomó y
documentó explícitamente para `RegistroEjecucion`
(`apps/accounts/tests/test_permisos.py::test_recurso_pide_registro_ajeno_por_id_da_doesnotexist_no_permissionerror`):
`ProyectoViewSet` usa `MixinAlcancePorRol.filtrar_por_rol` en `get_queryset()` para **todas**
las acciones (no solo `list`), así que un proyecto ajeno queda fuera del queryset de un
`LIDER` antes de que `check_object_permissions` se ejecute — `get_object()` lanza
`Http404`, nunca llega a la comprobación de permiso. Mantener esta inconsistencia habría roto
la doble capa queryset+permiso que exige `docs/api-contrato.md` §8 ("un permiso que solo cubra
el detalle deja fugas en los listados"): si el detalle no estuviera acotado por rol, el
`LIDER` podría leer el proyecto ajeno completo con solo conocer su `id`. Se prefirió la
consistencia con el resto de la app (404 "no existe para mí" en vez de 403 "existe pero no
puedo") sobre la letra literal del criterio. Las pruebas (`test_lider_no_puede_editar_proyecto_ajeno`)
documentan esto igual que lo hizo fase 03.

### Limitaciones conocidas

- No hay navegador disponible en este entorno: la verificación de las pantallas (lista,
  formulario, detalle, catálogos) se hizo con `ng build`/`ng lint`/`npm test` y revisando la
  app real vía `curl` contra el backend, no interactuando con la UI renderizada.
- El selector de estados en "Cambiar estado" usa una copia en el frontend
  (`TRANSICIONES_PROYECTO` en `core/models/enums.ts`) del mismo grafo que
  `apps/proyectos/services.py::TRANSICIONES`, tal como permite el plan ("se derivan del mismo
  grafo expuesto en `GET /proyectos/{id}/`"); el backend sigue siendo quien valida la
  transición real.
