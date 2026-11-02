# Fase 06 — Recursos, tarifas y asignación planeada

**Rama:** `fase-06-recursos-asignacion` · **Depende de:** fase 05 · **Esfuerzo:** 1–2 sesiones

## Objetivo

Construir el **lado planeado** del control presupuestal: catálogo de recursos con su historial
de tarifas y la asignación de recursos a proyectos, que es la que produce
`horas_planeadas` y `costo_planeado`. Sin esta fase el "versus ejecutado" no tiene contra qué
comparar.

## Precondiciones

- Fase 05 terminada.
- Lee `docs/modelo-datos.md` §4 y §10, y `docs/api-contrato.md` §5.

---

## Backend

### 6.1 Servicio de tarifas (pieza crítica)

1. `apps/recursos/services.py`:
   - `valor_hora_vigente(recurso, fecha)` → `Decimal`. Orden de resolución:
     1. `TarifaRecurso` cuyo rango `[vigente_desde, vigente_hasta]` contiene la fecha
        (`vigente_hasta` nulo significa "sin fin").
     2. `recurso.perfil.tarifa_hora_referencia`.
     3. Lanza `ErrorReglaNegocio` con el mensaje "El recurso X no tiene tarifa vigente al
        <fecha>; registre una tarifa o asígnele un perfil".
     **Esta función es la única autorizada para resolver tarifas en todo el sistema.**
   - `validar_vigencias(recurso, tarifa_nueva)` que detecta solapamientos y propone el ajuste
     ("cierre la tarifa anterior el <fecha>"). Al crear una tarifa nueva sin `vigente_hasta`,
     **cierra automáticamente** la anterior el día previo y lo informa en la respuesta.
   - `carga_recurso(recurso, desde, hasta)` → por mes: `horas_planeadas` (prorrateadas de las
     asignaciones que intersecan el mes), `horas_ejecutadas` (0 hasta la fase 08),
     `capacidad`, `pct_ocupacion`.
     El prorrateo se hace por días calendario de intersección y se documenta en el docstring.
2. `apps/recursos/services.py` (continuación):
   - `calcular_costo_planeado(asignacion)` → `horas_planeadas * valor_hora_plan`.
   - `validar_asignacion(asignacion)`: rango dentro de las fechas plan del proyecto (error),
     dedicación acumulada del recurso por mes > 100% (**advertencia**, no error),
     recurso inactivo o retirado antes de `fecha_hasta` (error).

### 6.2 API

3. CRUD de `Recurso` (`ViewSetBase`), filtros `tipo`, `perfil`, `activo`,
   `sin_asignacion=true`, `search_fields = ["nombre", "email"]`.
   Acciones: `GET /recursos/{id}/tarifas/`, `GET /recursos/{id}/carga/?desde=&hasta=`,
   `GET /recursos/{id}/asignaciones/`.
   Permisos: escritura `ADMIN` y `PMO`; lectura, todos.
4. CRUD de `TarifaRecurso` filtrable por `?recurso=`, que invoca `validar_vigencias`.
5. CRUD de `AsignacionRecurso` (`MixinAlcancePorRol`), filtros `proyecto`, `recurso`, `fase`.
   - Al crear, `valor_hora_plan` se **precarga** con `valor_hora_vigente(recurso, fecha_desde)`
     si no se envía; si se envía, se respeta el valor del usuario (puede negociarse una tarifa
     distinta) y se marca en bitácora que fue manual.
   - `costo_planeado` es calculado y de solo lectura.
   - La respuesta de creación y edición incluye `advertencias: []` cuando aplica
     (`docs/api-contrato.md` §5).
   - Permisos: `EsLiderDelProyecto` o `EsPmoOAdmin`.
6. `GET /proyectos/{id}/recursos-planeados/` → por recurso: horas, costo, periodo y fase.
7. Actualiza `apps/tablero/services.py`: ahora `horas_planeadas` y la parte de personal de
   `costo_planeado` ya tienen fuente real. **No reescribas las fórmulas**, solo verifica que
   el `annotate` lea de `AsignacionRecurso`. Ajusta las pruebas de §10 para que validen
   números reales en lugar de ceros.
8. Pruebas:
   - `valor_hora_vigente` en todos sus caminos, incluido el borde exacto de
     `vigente_desde` y `vigente_hasta`.
   - Crear una tarifa nueva cierra la anterior y no deja solapamiento.
   - Asignación fuera de las fechas del proyecto → 400 con mensaje.
   - Sobreasignación → 200 con `advertencias` no vacío.
   - `carga_recurso` con una asignación que cruza tres meses reparte las horas correctamente.
   - `resumen_ejecucion` de un proyecto con dos asignaciones da el `costo_planeado` esperado.

---

## Frontend

### 6.3 Pantallas

9. `features/recursos/` con `recursos.service.ts`, `tarifas.service.ts` y
   `asignaciones.service.ts`.
10. **Lista de recursos** (`/recursos`): tabla con nombre, tipo (`app-badge`), perfil,
    tarifa vigente hoy, capacidad mensual, número de proyectos activos, estado.
    Filtros: búsqueda, tipo, perfil, activo. Botón "Nuevo recurso" con permiso.
11. **Detalle de recurso** (`/recursos/:id`) con `app-tabs`:
    - *Datos*: formulario con vínculo opcional a un usuario (select con búsqueda de usuarios
      sin recurso asociado).
    - *Tarifas*: historial en tabla ordenado por `vigente_desde` descendente, con la vigente
      resaltada; alta de tarifa en modal que **avisa** que cerrará la anterior.
    - *Carga*: tabla por mes con horas planeadas, capacidad y `app-progreso` de ocupación;
      las filas por encima del 100% en color de alerta con texto "Sobreasignado".
12. **Asignaciones del proyecto**: en la pestaña *Recursos* del detalle de proyecto
    (la agregas al componente de la fase 05):
    - Tabla: recurso, rol en el proyecto, fase, periodo, dedicación, horas planeadas,
      valor hora, costo planeado; totales al pie (horas y costo).
    - Alta y edición en `app-drawer`. Al elegir recurso y fecha, el formulario consulta la
      tarifa vigente y precarga `valor_hora_plan` mostrando de dónde viene
      ("Tarifa vigente desde 01/01/2026"); si el usuario la cambia, se marca "Tarifa manual".
    - `costo_planeado` se muestra en vivo mientras se escribe (cálculo en cliente, pero el
      valor guardado es el que devuelve el servidor).
    - Las `advertencias` de la respuesta se muestran en un toast de tipo alerta, sin bloquear.
13. **Vista global de asignaciones** (`/recursos/asignaciones`): tabla multiproyecto con
    filtros por recurso, proyecto y rango de fechas, pensada para que el PMO detecte
    sobreasignación entre proyectos.

---

## Criterios de aceptación

- [x] Crear una tarifa con fecha que solapa la anterior la cierra sola y no deja huecos.
- [x] Un recurso sin tarifa ni perfil produce un error con mensaje accionable al asignarlo.
- [x] `GET /recursos/{id}/carga/` reparte bien las horas de una asignación que cruza meses.
- [x] Asignar un recurso al 60% en dos proyectos del mismo mes devuelve advertencia y guarda.
- [x] Asignar con fechas fuera del rango del proyecto se rechaza.
- [x] El `costo_planeado` del proyecto en la pestaña *Resumen* coincide con la suma de las
      asignaciones más los rubros.
- [x] Un `LIDER` asigna recursos en su proyecto y recibe 403 en uno ajeno.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/recursos -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Registro de horas ejecutadas (fase 08), nivelación automática de recursos, cálculo de costos
indirectos, vacaciones y festivos.

## Evidencia

### `pytest apps/recursos -q`

```
.............................                                            [100%]
29 passed in 34.36s
```

### `pytest` (suite completa del backend)

```
........................................................................ [ 38%]
........................................................................ [ 77%]
...........................................                              [100%]
187 passed in 166.54s
```

### `ruff check .`

```
All checks passed!
```

### `python manage.py spectacular --validate --fail-on-warn`

Sin advertencias ni errores.

### `npm run lint`

```
Linting "frontend"...
All files pass linting.
```

### `npm run build`

```
Application bundle generation complete.
Lazy chunks: lista, formulario, detalle (recursos), asignaciones-globales,
recursos-routes, además de los ya existentes de fase 05.
```

### `npm test`

```
Test Files  7 passed (7)
     Tests  31 passed (31)
```

### Verificación manual contra el backend real (`seed_demo`)

```
GET /recursos/{id}/  → tarifa_vigente, perfil_nombre, proyectos_activos resueltos
GET /recursos/{id}/tarifas/ → historial
GET /recursos/{id}/carga/?desde=&hasta= → horas_planeadas/capacidad/pct_ocupacion por mes
GET /proyectos/{id}/resumen/ → costo_planeado y horas_planeadas ya con fuente real en
    AsignacionRecurso (antes de esta fase daban 0 siempre)
GET /proyectos/{id}/recursos-planeados/ → asignaciones del proyecto con costo_planeado
```

### Bugs reales encontrados y corregidos durante esta fase

1. **Regresión introducida por mí mismo y detectada por la suite existente antes de
   commitear**: al generalizar `EsLiderDelProyecto.has_permission` para que los `ViewSet` de
   sub-recursos (fases, hitos, rubros, y ahora asignaciones) pudieran usarla directamente sin
   envolverla, añadí un bypass de `SAFE_METHODS` dentro de `has_object_permission` de la
   propia clase base. Esto rompió el comportamiento ya establecido y probado en fase 03
   (`test_es_lider_del_proyecto_autoriza_al_gerente_y_al_lider_tecnico`): un `LIDER` pasaba a
   poder **leer** el detalle de una `Tarea` ajena. La causa es que `EsLiderDelProyecto` se usa
   en dos contextos distintos — "solo el dueño puede tocar esto, ni para leer" (el caso
   general, p. ej. `Tarea`) y "cualquiera lee, solo el dueño escribe" (el caso de los
   sub-recursos de un proyecto, donde `MixinAlcancePorRol` ya acota el listado). Se separó en
   dos clases: `EsLiderDelProyecto` (sin cambios de comportamiento respecto a fase 03) y la
   nueva `EsLiderDelProyectoOLectura` (con el bypass de lectura), y se corrigieron los
   `ViewSet` de proyectos y recursos para usar la que corresponde. La suite completa (187
   pruebas) quedó verde después de separar las clases.
2. **`MixinAlcancePorRol._alcance_recurso` no tenía un caso especial para
   `AsignacionRecurso`** (solo para `Tarea` y `RegistroEjecucion`): un `RECURSO` consultando
   `/asignaciones/` vería las asignaciones de **todo el proyecto** donde tiene una asignación,
   no solo las suyas. Se agregó el caso especial, igual que para `RegistroEjecucion`.

### Discrepancia documentada (no es un bug)

`docs/plan/fase-06-recursos-asignacion.md` §6.1 pide que el formulario de asignación consulte
"la tarifa vigente" al elegir recurso y fecha. La API no expone un endpoint para resolver
`valor_hora_vigente(recurso, fecha)` a una fecha arbitraria desde el frontend (solo el
servidor la usa internamente al crear la asignación). El formulario de la pestaña *Recursos*
del proyecto precarga el campo con la tarifa vigente **hoy** del recurso (vía
`GET /recursos/{id}/` → `tarifa_vigente`) a modo de referencia visual y lo aclara en texto; si
el usuario no la modifica, el campo se omite al guardar y el servidor resuelve la tarifa
vigente real a la fecha "desde" (que es la que efectivamente queda guardada). Si se necesita
la vista previa exacta a una fecha pasada o futura, una fase posterior podría agregar un
endpoint dedicado.

### Limitación conocida detectada (fuera de alcance de esta fase)

Al re-ejecutar `python manage.py seed_demo` en un día calendario distinto dentro de esta misma
sesión, se crearon asignaciones adicionales en vez de no hacer nada (su `fecha_desde`
depende de la fecha de ejecución, así que el `UniqueConstraint(proyecto, recurso, fase,
fecha_desde)` no detecta la repetición). El comando no es realmente idempotente entre días
distintos. Es un bug de `apps/core/management/commands/seed_demo.py` (fase 01), fuera del
alcance de esta fase; se deja anotado para que una fase posterior lo corrija anclando las
fechas sembradas a la fecha del *primer* `seed_demo` en vez de a "hoy", o usando
`get_or_create`.
