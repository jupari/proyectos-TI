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

- [ ] Un `PMO` crea un proyecto y el código se genera solo con el formato `PRY-2026-001`.
- [ ] Un `LIDER` edita su proyecto y recibe 403 al editar uno ajeno.
- [ ] Un `RECURSO` no ve el botón "Nuevo proyecto" ni puede acceder a `/proyectos/nuevo`.
- [ ] Guardar fases cuyos pesos suman 90 falla con un mensaje que dice cuánto falta.
- [ ] Un presupuesto menor que la suma de rubros se rechaza con mensaje claro.
- [ ] Pasar de `BORRADOR` a `CERRADO` se rechaza con 409 y la lista de transiciones válidas.
- [ ] Pasar a `EJECUCION` sin asignaciones se rechaza con el motivo exacto.
- [ ] Los filtros de la lista quedan en la URL y sobreviven a recargar la página.
- [ ] El detalle de un proyecto de `seed_demo` muestra su semáforo y sus KPIs sin errores.
- [ ] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios, OpenAPI válido.

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

<!-- Pega aquí la salida real de los comandos de verificación. -->
