# Fase 08 — Ingesta de ejecución: horas y gastos

**Rama:** `fase-08-ejecucion-ingesta` · **Depende de:** fase 07 · **Esfuerzo:** 2 sesiones

## Objetivo

El corazón de la aplicación (objetivos 1.3 y 5): capturar la ejecución real de los recursos
con periodicidad **diaria, semanal o mensual**, aprobarla, y producir el contraste
**planeado vs. ejecutado** en horas y en dinero.

## Precondiciones

- Fase 07 terminada.
- Lee `docs/modelo-datos.md` §6 y §10, `docs/api-contrato.md` §6, y
  `apps/core/periodos.py` de la fase 02 (ya tiene la normalización de periodos probada).

---

## Backend

### 8.1 Servicios de ingesta

1. `apps/ejecucion/services.py`:
   - `preparar_registro(datos)`:
     1. `normalizar_periodo(periodicidad, periodo_inicio)` → fija `periodo_inicio` y `periodo_fin`.
     2. `valor_hora_aplicado = valor_hora_vigente(recurso, periodo_inicio)` si no se envía.
     3. `costo = horas * valor_hora_aplicado`.
   - `validar_solapamiento(registro)`: busca registros del **mismo recurso y proyecto** cuyos
     rangos `[periodo_inicio, periodo_fin]` intersequen el del registro nuevo, con cualquier
     periodicidad, en estado distinto de `RECHAZADO`. Si hay, lanza `ErrorReglaNegocio` (422)
     con la lista de registros en conflicto en `detalles.conflictos`
     (`[{id, periodicidad, periodo_inicio, periodo_fin, horas}]`).
     **Esta validación es la que impide contar las mismas horas dos veces** y es obligatoria.
   - `validar_topes(registro)`: diaria ≤ 24 h, semanal ≤ 60 h,
     mensual ≤ `capacidad_horas_mes * 1.5`. Devuelve **advertencias**, no errores.
   - `validar_rango_proyecto(registro)`: el periodo debe intersecar las fechas del proyecto
     (plan o real). Fuera de rango → 400.
   - `validar_tarea(registro)`: si trae `tarea`, debe pertenecer al `proyecto` y no estar
     `CANCELADA`.
   - `enviar(registro, usuario)`, `aprobar(registro, usuario)`, `rechazar(registro, motivo,
     usuario)`, `reabrir(registro, usuario)`: aplican las transiciones de
     `BORRADOR → ENVIADO → APROBADO | RECHAZADO` y `APROBADO → ENVIADO` (reabrir).
     Cada una escribe `registrar_evento` con el tipo correspondiente.
     **Nadie aprueba su propio registro**: si `registrado_por == usuario` y el usuario no es
     `ADMIN`, 403 con mensaje explícito.
   - `recalcular_derivados(registro)`: actualiza `Tarea.horas_ejecutadas` y
     `RubroPresupuesto.monto_ejecutado` sumando **solo** lo aprobado. Se invoca al aprobar,
     rechazar y reabrir, dentro de la misma transacción.
   - `carga_lote(lista, usuario)`: procesa cada registro de forma independiente, devuelve
     `{creados, errores: [{indice, detalle}]}`; los válidos se guardan aunque otros fallen.
     Cada registro se guarda en su propia `transaction.atomic()` anidada (`savepoint`).

### 8.2 API

2. `RegistroEjecucionViewSet(ViewSetBase, MixinAlcancePorRol)` con todos los filtros y
   acciones de `docs/api-contrato.md` §6:
   - `PATCH` permitido solo en `BORRADOR` y `RECHAZADO`; en otro estado, 409.
   - `APROBADO` es inmutable: cualquier escritura devuelve 409 con el mensaje
     "Reabra el registro para modificarlo".
   - `registrado_por` lo fija el servidor con el usuario de la petición, nunca el cliente.
   - Un `RECURSO` solo puede crear registros **de su propio recurso**
     (`recurso.usuario == request.user`); si envía otro, 403.
   - `GET /registros-ejecucion/resumen/?proyecto=&agrupar_por=recurso|tarea|mes` con
     `values().annotate(Sum(...))`, nunca iterando en Python.
3. `GastoEjecutadoViewSet` con el mismo ciclo de aprobación y la validación de que el `rubro`
   pertenece al proyecto.
4. `GET /proyectos/{id}/ejecucion/` → bloque comparativo por recurso y por mes:
   `[{recurso, horas_plan, horas_ejec, costo_plan, costo_ejec, pct_horas, pct_dinero}]`.
5. Actualiza `apps/tablero/services.py`: con esta fase `horas_ejecutadas` y `costo_ejecutado`
   ya tienen fuente real, así que `resumen_ejecucion` queda completo, incluidos `SPI`, `CPI`
   y `desviacion_presupuestal`. **Las fórmulas de §10 no se tocan**; solo se verifica que
   sumen únicamente lo `APROBADO` y que `horas_pendientes_aprobacion` cuente lo `ENVIADO`.
6. Pruebas (las más importantes del proyecto):
   - Normalización: un registro semanal creado con fecha de miércoles queda de lunes a domingo.
   - Duplicado exacto → 400 por la restricción única.
   - Un mensual de marzo más un diario del 15 de marzo del mismo recurso y proyecto → 422 con
     los conflictos listados.
   - Dos registros del mismo recurso en **proyectos distintos** en el mismo día → permitido.
   - Tope excedido → 200 con advertencia.
   - Aprobar suma a `Tarea.horas_ejecutadas`; rechazar lo resta; reabrir lo resta.
   - Un registro rechazado no entra en los KPIs.
   - El propio autor no puede aprobar su registro; el `LIDER` del proyecto sí.
   - `PATCH` sobre un registro aprobado → 409.
   - Un `RECURSO` no puede registrar horas a nombre de otro.
   - `carga_lote` con 5 registros, 2 inválidos: crea 3 y reporta 2 errores con su índice.
   - `resumen_ejecucion` de un proyecto completo de `seed_demo` da los valores esperados,
     calculados a mano en la prueba (no comparando el código contra sí mismo).

---

## Frontend

### 8.3 Pantallas

7. `features/ejecucion/data/` con `registros.service.ts` y `gastos.service.ts`.
8. **Mi registro de horas** (`/ejecucion/registros`) — la pantalla que más se usa:
    - Selector de periodicidad (diaria, semanal, mensual) y navegador de periodo
      (anterior / siguiente / hoy) que muestra el rango resuelto en texto
      ("Semana del 26 oct al 1 nov de 2026").
    - **Cuadrícula de captura**: filas = proyecto y tarea asignados al usuario;
      columnas = días del periodo (en diaria y semanal) o una sola columna (en mensual).
      Total por fila, total por columna y total general en vivo.
    - Guardado por fila con `app-boton` en estado `cargando`; o botón "Guardar todo" que usa
      `POST /registros-ejecucion/lote/` y muestra un resumen de creados y errores.
    - Estado de cada celda visible con `app-badge` (borrador, enviado, aprobado, rechazado);
      las celdas aprobadas se muestran bloqueadas con candado y tooltip explicativo.
    - Los motivos de rechazo se muestran en la celda correspondiente.
    - Las advertencias de tope se muestran en toast de alerta sin impedir el guardado.
    - Botón "Enviar a aprobación" que envía todo lo que esté en borrador del periodo.
9. **Aprobaciones** (`/ejecucion/aprobaciones`), visible con `ejecucion.aprobar`:
    - Tabla de registros en `ENVIADO` con proyecto, recurso, periodo, horas, costo y
      descripción; selección múltiple; botones "Aprobar seleccionados" y "Rechazar
      seleccionados" (este pide el motivo en modal, obligatorio).
    - Filtros por proyecto, recurso y rango de periodo.
    - Contador en el menú lateral con el número de registros pendientes de aprobación.
10. **Pestaña *Ejecución* del proyecto** (completa el marcador de la fase 05):
    - Tarjetas: horas plan vs. ejecutadas, dinero plan vs. ejecutado, % de avance
      presupuestal, `app-semaforo` y desviación.
    - Tabla comparativa por recurso: plan, ejecutado, diferencia, % de consumo
      (`app-progreso` con color por umbral: verde <90, amarillo 90–100, rojo >100).
    - Tabla por mes con las mismas columnas.
    - Sección de gastos (rubros no de personal) con su propio ciclo de aprobación.
    - Aviso visible cuando hay horas pendientes de aprobación, con el total, para que nadie
      lea los KPIs como definitivos sin saberlo.
11. **Gastos ejecutados**: alta en modal desde la pestaña de presupuesto, con selector de
    rubro del proyecto, monto, proveedor, número de documento y fecha.

---

## Criterios de aceptación

- [x] Un `RECURSO` registra horas diarias de una semana y los totales cuadran.
- [x] Un registro semanal creado desde un miércoles se normaliza a lunes-domingo.
- [x] Intentar un registro mensual que solapa uno diario existente muestra en la UI la lista
      de registros en conflicto.
- [x] Un `LIDER` aprueba un lote de registros y los KPIs del proyecto cambian al instante.
- [x] Un registro rechazado muestra su motivo al recurso y no cuenta en los KPIs.
- [x] Nadie puede aprobar su propio registro (salvo `ADMIN`).
- [x] Un registro aprobado no se puede editar; al reabrirlo sí, y queda en bitácora.
- [x] `Tarea.horas_ejecutadas` coincide con la suma de los registros aprobados de esa tarea.
- [x] La pestaña *Ejecución* muestra plan vs. ejecutado por recurso y por mes con los valores
      correctos y avisa de lo pendiente de aprobación.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/ejecucion apps/tablero -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Seguimientos y expediente (fase 09), tablero global (fase 10), importación desde Excel,
aprobación en varios niveles, integración con nómina.

## Evidencia

### Backend

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/ejecucion apps/tablero -q
......................................................                   [100%]
54 passed in 42.98s

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
.......................................................................  [100%]
287 passed in 151.98s (0:02:31)

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
(sin warnings/errores; exit 0)
```

### Frontend

```
$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
Linting "frontend"...
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npm run build
Application bundle generation complete. [14.4s]
Output location: /app/dist/frontend
(chunks nuevos: mi-registro, aprobaciones)

$ docker compose -f infra/docker-compose.yml exec frontend npm test -- --watch=false
Test Files  7 passed (7)
     Tests  31 passed (31)
```
(`npm test` no es un comando de verificación exigido por esta fase; se corrió para confirmar
que nada de fases anteriores se rompió. Las pantallas nuevas no tienen specs propios porque
la fase no lo exige — igual que en la fase 07.)

### Verificación manual contra el backend real (`seed_demo`, sin navegador disponible)

Con `admin@seguimiento.local` contra `PRY-2026-001`:

- `POST /registros-ejecucion/` diario (8 h) → 201, `valor_hora_aplicado` resuelto de la tarifa
  vigente del recurso, `costo` calculado por el modelo (`horas * valor_hora_aplicado`).
- La misma petición repetida exacta → **400** (lo produce el chequeo explícito de duplicado
  exacto añadido a `validar_solapamiento`; ver la discrepancia documentada más abajo sobre por
  qué DRF no lo detecta solo).
- `POST .../enviar/` → `ENVIADO`; `POST .../aprobar/` → `APROBADO`.
- `PATCH` sobre el registro ya `APROBADO` → **409** `"Reabra el registro para modificarlo."`.
- `GET /proyectos/{id}/ejecucion/` → `por_recurso`/`por_mes` con `horas_ejec`/`costo_ejec` ya
  reflejando el registro aprobado (se confirmó que los valores llegan como **float**, no
  string, porque la acción devuelve un diccionario plano, no un serializer — igual que en
  fases anteriores).
- `POST /registros-ejecucion/lote/` con 2 registros válidos y 1 incompleto (`{"proyecto":
  "..."}`, sin recurso/periodicidad/periodo_inicio/horas) → `{"creados": 2, "errores":
  [{"indice": 2, "detalle": {...campos obligatorios...}}]}`: el comportamiento parcial (los
  válidos entran aunque otro falle) quedó confirmado.
- `GET /registros-ejecucion/resumen/?agrupar_por=recurso` → agregados por recurso, floats.
- Ciclo completo de `GastoEjecutado`: crear (`BORRADOR`) → enviar → aprobar → el
  `RubroPresupuesto.monto_ejecutado` del rubro subió exactamente el monto del gasto.
- Todos los datos de prueba se limpiaron al terminar (`DELETE`/borrado directo) y se restauró
  la contraseña del usuario admin a su estado inicial (inutilizable).

No hay navegador disponible en este entorno (igual que en fases 05-07): la cuadrícula de "Mi
registro de horas", el flujo de aprobaciones y la pestaña *Ejecución* del proyecto se
verificaron por `ng build`/`ng lint` (sin errores de plantilla) y por los datos reales que
consumen vía `curl`, no renderizados pixel a pixel en un navegador real.

### Decisiones y discrepancias documentadas

1. **`docs/modelo-datos.md` §6 decía "Error 400" para el solapamiento de periodos; el plan de
   esta fase (§8.1.2) pedía `ErrorReglaNegocio` (422) con `detalles.conflictos`.** Se mantuvo
   422 para el solapamiento genuino (es un conflicto de reglas de negocio, no un dato mal
   formado) y se descubrió en el camino que el **duplicado exacto** (mismo recurso, proyecto,
   tarea, periodicidad y `periodo_inicio`, que es literalmente `registroejecucion_unico`)
   necesitaba su propio camino a 400: DRF **no genera automáticamente** el validador de
   `UniqueConstraint` para ese campo porque `tarea` es nullable (DRF no puede garantizar
   unicidad cuando uno de los campos puede ser `NULL`, ya que `NULL` nunca es "igual" a `NULL`
   en SQL). Sin ese validador automático, un duplicado exacto caía en el mismo camino que un
   solapamiento genérico y devolvía 422, no el 400 que pide el criterio de aceptación "Un
   registro mensual que solapa uno diario... 422 con conflictos" (que sí es genérico) versus
   el bullet de pruebas "Duplicado exacto → 400 por la restricción única" (que es un caso
   específico). Se resolvió añadiendo una comprobación explícita de coincidencia exacta al
   principio de `validar_solapamiento`, antes de la comprobación genérica de solapamiento.
2. **`recalcular_derivados(registro)` del plan se implementó como dos funciones separadas**,
   `recalcular_tarea` (para `RegistroEjecucion` → `Tarea.horas_ejecutadas`) y `recalcular_rubro`
   (para `GastoEjecutado` → `RubroPresupuesto.monto_ejecutado`): `RegistroEjecucion` no tiene
   `rubro` ni `GastoEjecutado` tiene `tarea`, así que una sola función con un parámetro
   `registro` no podía actualizar ambos destinos a la vez como sugiere la redacción del plan.
3. **`GastoEjecutado` no tiene el chequeo de autoaprobación** que sí tiene `RegistroEjecucion`:
   el modelo no tiene un campo `registrado_por` (confirmado en `docs/modelo-datos.md` §6, que
   solo le da `aprobado_por`/`aprobado_en`), así que no hay nada contra qué comparar.
4. **El permiso de `GastoEjecutado` es más estricto que el de `RegistroEjecucion` para `LIDER`**:
   la matriz de `docs/api-contrato.md` §8 dice "L C *propios*" para gastos (sin `E` ni `A`),
   a diferencia de "L C E A *propios*" para registros de horas. Un `LIDER` puede crear un gasto
   en su proyecto pero no puede editarlo, enviarlo ni aprobarlo — eso queda en manos de PMO/
   ADMIN. Se implementó tal cual lo dice la matriz, aunque la redacción de la fase ("mismo
   ciclo de aprobación") podría sugerir permisos idénticos; la matriz de permisos es la fuente
   de verdad de roles, no la descripción general del flujo.
5. **`apps/tablero/services.py::_metricas` tenía un bug real preexistente**: calculaba
   `horas_pendientes_aprobacion` como `total - aprobado` (es decir, `BORRADOR + ENVIADO +
   RECHAZADO` combinados), cuando el plan pide explícitamente que cuente solo lo `ENVIADO`. Se
   corrigió a una suma filtrada por `estado_aprobacion=ENVIADO`, y se añadió una prueba con
   `BORRADOR`, `ENVIADO`, `RECHAZADO` y `APROBADO` simultáneos para que no se repita.
6. **"Mi registro de horas" interpreta "columnas = días del periodo (en diaria y semanal)"
   como: la cuadrícula siempre muestra columnas por día (una semana) tanto en `DIARIA` como en
   `SEMANAL`; lo que cambia es cómo se guarda cada fila al presionar "Guardar": en `DIARIA` cada
   celda con valor se guarda como un `RegistroEjecucion` independiente (`periodo_inicio` =
   ese día); en `SEMANAL`, todas las celdas de la fila se suman en un único registro con
   `periodo_inicio` = el lunes de esa semana. En `MENSUAL` se muestra una sola columna. El plan
   no fija esta mecánica con el mismo nivel de detalle que otras reglas, así que queda
   documentada aquí como la lectura adoptada. Una consecuencia de este diseño: una vez guardado
   un registro `SEMANAL`, los días martes a domingo de esa fila quedan bloqueados (ya están
   "ocupados" por ese registro); para corregir el total hay que editar la celda del lunes.
7. **El contador de aprobaciones pendientes del menú lateral** solo hace una petición
   (`?estado_aprobacion=ENVIADO&page_size=1`, usando `count` de la paginación) y solo si el
   usuario tiene `ejecucion.aprobar`; no se actualiza en tiempo real mientras la sesión está
   abierta (se recalcula al recargar la aplicación), que es una limitación aceptada para no
   añadir polling o websockets en esta fase.
8. **Se agregó el filtro `usuario` a `FiltroRecurso`** (`apps/recursos/filters.py`), fuera del
   alcance literal de esta fase pero necesario para que "Mi registro de horas" pueda resolver
   el `Recurso` del usuario autenticado sin traer la lista completa de recursos; es un cambio
   mínimo y acorde al modelo ya existente (`Recurso.usuario`), con su propia prueba en
   `apps/recursos/tests/test_api.py`.

## Adenda: el contador del menú llevaba a una pantalla sin relación visible

El contador rojo de "Ejecución" en el menú lateral (punto 7 arriba) cuenta los
`RegistroEjecucion` en `ENVIADO` de **todo lo que el usuario puede aprobar** — para un `ADMIN`,
de todos los proyectos. Pero el ítem del menú apunta a `/ejecucion/registros` ("Mi registro de
horas", la agenda **personal** de quien entra, filtrada a sus propias tareas asignadas en la
semana actual), no a `/ejecucion/aprobaciones` (la cola de aprobación donde viven esos
pendientes). Si la persona no tiene tareas propias asignadas esa semana, aterriza en una pantalla
vacía sin ninguna pista de a dónde ir a ver lo que el número anuncia — se reportó como "aparece
un indicador de 179 y la vista no tiene nada".

Se agregó una pestañita (`Mis registros` / `Aprobaciones`, con el mismo contador) arriba de
ambas pantallas, visible solo si la persona tiene el otro permiso además del de la pantalla en la
que está (`ejecucion.registrar` y/o `ejecucion.aprobar`), para poder moverse entre las dos sin
adivinar la URL. De paso, `aprobarSeleccionados()`/`confirmarRechazoSeleccionados()` en
`Aprobaciones` ahora llaman a `ContadorAprobacionesService.actualizar()` al terminar el lote, así
que el número del menú baja de inmediato al aprobar/rechazar, no solo al recargar la aplicación
(la limitación del punto 7 sigue siendo cierta entre pestañas/sesiones distintas, pero ya no
dentro de la misma sesión después de actuar sobre la cola).
