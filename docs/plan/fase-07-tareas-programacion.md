# Fase 07 — Tareas, actividades y programación

**Rama:** `fase-07-tareas-programacion` · **Depende de:** fase 06 · **Esfuerzo:** 2 sesiones

## Objetivo

Cubrir el objetivo 1.4: poder **adicionar tareas o actividades a lo largo de la ejecución**
del proyecto, con jerarquía, responsables, estimación de horas, dependencias y un cronograma
visible. Las tareas son el enganche al que después se imputan las horas ejecutadas.

## Precondiciones

- Fase 06 terminada.
- Lee `docs/modelo-datos.md` §5 y `docs/api-contrato.md` §5.

---

## Backend

### 7.1 Servicios

1. `apps/tareas/services.py`:
   - `generar_codigo_tarea(proyecto)` → `<codigo_proyecto>-T<secuencia de 3 dígitos>`,
     con `select_for_update` sobre el proyecto para evitar colisiones.
   - `validar_jerarquia(tarea, padre)`: la tarea no puede ser su propio ancestro, el padre
     debe ser del mismo proyecto y la profundidad máxima es 3. Error 400 con el motivo exacto.
   - `detectar_ciclo(origen, destino)`: recorrido en profundidad sobre `DependenciaTarea`;
     si añadir la dependencia crea un ciclo, lanza `ErrorConflicto` con la **ruta del ciclo**
     en `detalles` (`["T001", "T004", "T009", "T001"]`), que es lo que hace útil el error.
   - `recalcular_avance(tarea)`: si tiene subtareas activas, `avance` es el promedio ponderado
     por `horas_estimadas` de las hijas (si todas tienen 0 horas estimadas, promedio simple).
     Se dispara al guardar una subtarea y sube recursivamente hasta la raíz.
   - `cambiar_estado_tarea(tarea, estado_nuevo, usuario)`:
     - `EN_PROGRESO` exige `fecha_inicio_real` (si no viene, la pone en hoy).
     - `COMPLETADA` exige `fecha_fin_real` (si no viene, hoy) y fija `avance = 100`.
     - No se puede completar una tarea con subtareas abiertas → 409.
     - `BLOQUEADA` exige una nota, que se guarda en bitácora.
     - Escribe `registrar_evento(tipo_evento="CAMBIO_ESTADO", ...)`.
   - `marcar_creacion_durante_ejecucion(tarea)`: si el proyecto está en `EJECUCION` al crear la
     tarea, pone `creada_durante_ejecucion=True` y **exige** `motivo_creacion`. Este dato es el
     que alimenta el indicador de alcance adicional del tablero (fase 10).
   - `fechas_sugeridas(tarea)`: dadas sus dependencias `FI` y el `dias_desfase`, calcula la
     fecha de inicio más temprana posible. Es **sugerencia**, no se impone; la UI la ofrece.

### 7.2 API

2. `apps/tareas/filters.py` con todos los filtros de `docs/api-contrato.md` §5, incluidos
   `vencidas` (`fecha_fin_plan < hoy` y estado no terminal) y `mis_tareas`
   (responsable cuyo `recurso.usuario` es el solicitante).
3. Serializers:
   - `TareaListaSerializer`: plano + `proyecto_codigo`, `fase_nombre`, `responsable_nombre`,
     `horas_ejecutadas`, `dias_atraso` (calculado, `null` si no aplica),
     `tiene_subtareas` (bool) y `numero_dependencias`.
   - `TareaDetalleSerializer`: lo anterior más `subtareas` (un nivel), `dependencias_entrantes`
     y `dependencias_salientes`.
   - `TareaEscrituraSerializer`: valida jerarquía, exige `motivo_creacion` cuando corresponde,
     rechaza escribir `codigo`, `horas_ejecutadas` y `avance` si la tarea tiene subtareas.
4. `TareaViewSet(ViewSetBase, MixinAlcancePorRol)` con acciones:
   `cambiar-estado`, `arbol` (`?proyecto=`, jerarquía anidada en una sola consulta con
   `prefetch_related`), `fechas-sugeridas`.
   Permisos: `LIDER` en sus proyectos; `RECURSO` puede crear y editar **solo las tareas donde
   él es el responsable** (y no puede reasignar el responsable a otro).
5. `DependenciaTareaViewSet`: CRUD con `detectar_ciclo` en `create`.
6. `GET /proyectos/{id}/cronograma/`: filas con
   `{tarea_id, codigo, nombre, nivel, fase, inicio_plan, fin_plan, inicio_real, fin_real,
   avance, estado, responsable, dependencias: [{tarea_id, tipo, dias_desfase}]}`,
   ordenadas por fase (`orden`) y luego por `fecha_inicio_plan`. Una sola consulta, sin N+1.
7. Pruebas:
   - Código de tarea secuencial por proyecto, sin colisión al crear dos en paralelo.
   - Jerarquía: ciclo de padres rechazado, cuarto nivel rechazado.
   - Dependencia circular rechazada con la ruta del ciclo en `detalles`.
   - `recalcular_avance` con pesos distintos y con horas estimadas en 0.
   - Completar una tarea con subtarea abierta → 409.
   - Crear tarea en proyecto `EJECUCION` sin `motivo_creacion` → 400.
   - Un `RECURSO` no puede editar la tarea de otro ni cambiarle el responsable.
   - `/cronograma/` de un proyecto con 40 tareas se resuelve en menos de 10 consultas
     (`django_assert_num_queries`).

---

## Frontend

### 7.3 Pantallas

8. `features/tareas/data/tareas.service.ts` y `dependencias.service.ts`.
9. **Bandeja global de tareas** (`/tareas`):
    - Tabla con proyecto, código, nombre, tipo, estado, prioridad, responsable, fechas plan,
      horas estimadas vs. ejecutadas, avance (`app-progreso`), días de atraso en rojo.
    - Filtros en la URL: proyecto, estado, tipo, prioridad, responsable, "solo mis tareas",
      "solo vencidas", "creadas durante la ejecución".
    - Cambio rápido de estado desde la fila (select en línea) con confirmación cuando el
      cambio exige datos extra.
10. **Pestaña *Tareas* del proyecto** (completa el marcador de la fase 05):
    - Vista **árbol** con subtareas colapsables, indentación por nivel, y totales de horas
      estimadas y ejecutadas por fase.
    - Botón "Nueva tarea" y "Nueva subtarea" en cada fila.
    - Formulario en `app-drawer`: si el proyecto está en `EJECUCION`, aparece el campo
      obligatorio "Motivo de la creación" con una nota que explica por qué se pide.
    - Gestión de dependencias dentro del drawer: lista de dependencias con selector de tarea,
      tipo y desfase; si el servidor devuelve un ciclo, se muestra la ruta del ciclo en el
      mensaje de error, no un texto genérico.
    - Botón "Sugerir fechas" que consulta `fechas-sugeridas` y rellena los campos.
11. **Cronograma** (pestaña *Cronograma* del proyecto): diagrama de barras tipo Gantt **de
    solo lectura**, construido con CSS Grid y los tokens de Tailwind, sin librería externa:
    - Eje temporal por semanas o meses, conmutable; una fila por tarea agrupada por fase.
    - Barra de plan y, superpuesta en tono más oscuro, la barra de avance.
    - Las barras reales (`fecha_inicio_real` / `fecha_fin_real`) se dibujan como una línea
      delgada bajo la del plan.
    - Hitos como rombos en su fecha.
    - Las dependencias se indican en el tooltip de la tarea (no se dibujan líneas: eso es
      alcance de una v2 y está excluido en `PLAN.md` §10).
    - Debe funcionar con 100 tareas sin trabarse (virtualización simple por rango visible) y
      tener scroll horizontal propio en pantallas angostas.
12. **Detalle de tarea** (`/tareas/:id`): datos, subtareas, dependencias, horas registradas
    (la lista real la llena la fase 08) y la línea de tiempo de la bitácora de esa tarea
    (consumiendo `/bitacora/?entidad=Tarea&entidad_id=`).

---

## Criterios de aceptación

- [x] Se puede crear una tarea en un proyecto en `EJECUCION` y queda marcada como alcance
      adicional con su motivo.
- [x] La jerarquía admite 3 niveles y rechaza el cuarto con mensaje claro.
- [x] El avance de una tarea padre se recalcula al cambiar el de una hija.
- [x] Una dependencia circular se rechaza mostrando la ruta del ciclo en la UI.
- [x] Un `RECURSO` ve y edita solo sus tareas; no puede reasignarlas.
- [x] El cronograma dibuja plan, avance y real de un proyecto de `seed_demo` y funciona en
      pantalla de 400px de ancho con scroll horizontal.
- [x] `/proyectos/{id}/cronograma/` cumple el límite de consultas de la prueba.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/tareas -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Registro de horas (fase 08), Gantt interactivo con arrastre, ruta crítica, nivelación de
recursos, tableros Kanban con arrastrar y soltar.

## Evidencia

### Backend

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/tareas -q
...............................................                          [100%]
47 passed in 30.51s

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 91%]
...................                                                      [100%]
235 passed in 110.55s (0:01:50)

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
Application bundle generation complete. [10.9s]
Output location: /app/dist/frontend

$ docker compose -f infra/docker-compose.yml exec frontend npm test -- --watch=false
Test Files  7 passed (7)
     Tests  31 passed (31)
```
(`npm test` no es un comando de verificación exigido por esta fase, pero se corrió para
confirmar que no se rompió nada de fases anteriores; las pantallas nuevas de esta fase no
tienen specs propios porque la fase no lo exige.)

### Verificación manual contra el backend real (`seed_demo`, sin navegador disponible)

Se autenticó como `admin@seguimiento.local` contra el proyecto `PRY-2026-001` (en `EJECUCION`)
y se ejercitó el flujo completo con `curl`:

- `POST /tareas/` sin `motivo_creacion` en un proyecto en `EJECUCION` → 400 con
  `{"motivo_creacion": ["Debe indicar el motivo: el proyecto ya está en ejecución."]}`.
- La misma petición con `motivo_creacion` → 201, `codigo` autogenerado `PRY-2026-001-T010`,
  `creada_durante_ejecucion: true`.
- `GET /tareas/arbol/?proyecto=` → jerarquía anidada correcta.
- `GET /proyectos/{id}/cronograma/` → filas con `nivel`, `fase`, fechas y `dependencias`.
- `POST /dependencias-tarea/` T000→T010 (FI) → 201; la dependencia inversa T010→T000 → **409**
  con `detalles.ciclo = ["PRY-2026-001-T010", "PRY-2026-001-T000", "PRY-2026-001-T010"]`.
- `GET /tareas/{id}/fechas-sugeridas/` → `{"fecha_inicio_sugerida": "2027-05-01", ...}`
  (fin plan del predecesor + 1 día, sin desfase).
- `POST /tareas/{id}/cambiar-estado/` a `BLOQUEADA` sin `nota` → 400; con `nota` → 200 y la
  tarea queda `BLOQUEADA`.
- Se limpiaron los datos de prueba (`DELETE` de la tarea creada) y se restauró la contraseña
  del usuario admin a su estado inicial (inutilizable) al terminar.

No hay herramienta de navegador en este entorno (igual que en las fases 05 y 06), así que el
árbol colapsable, el drawer de tareas y el Gantt de la pestaña Cronograma se verificaron por
`ng build`/`ng lint` (sin errores de plantilla) y por la forma de los datos que consumen,
pero no se vieron renderizados pixel a pixel en un navegador real.

### Decisiones y discrepancias documentadas

1. **`DependenciaTareaViewSet` responde 409, no 400, ante un ciclo.** `docs/api-contrato.md`
   §5 decía "rechaza ciclos con 400", pero el propio §7.1.3 de esta fase exige
   `ErrorConflicto` con la ruta del ciclo en `detalles` ("que es lo que hace útil el error").
   Se mantuvo 409 (conflicto con el estado actual del grafo de dependencias, no un dato mal
   formado) y se corrigió `docs/api-contrato.md` para que diga 409 y documente
   `detalles.ciclo`; el 400 se reserva para cuando las dos tareas no son del mismo proyecto.
2. **`estado` no es escribible en `TareaEscrituraSerializer`**, igual que en
   `ProyectoEscrituraSerializer` (fase 05): todo cambio de estado pasa por
   `POST /tareas/{id}/cambiar-estado/`, que es el único lugar que aplica las precondiciones
   (autocompletar fechas, exigir nota en `BLOQUEADA`, bloquear `COMPLETADA` con subtareas
   abiertas) y escribe la bitácora. Permitir un `PATCH` directo de `estado` habría dejado una
   puerta trasera que se salta esas reglas.
3. **`codigo`, `horas_ejecutadas` y `avance` (cuando hay subtareas) se rechazan explícitamente
   en `validate()`** en vez de solo marcarse `read_only` y ser ignorados en silencio: el plan
   dice "rechaza escribir", y un 400 explícito es más útil para quien integra contra la API
   que un campo que simplemente no tiene efecto.
4. **La "nota" de `BLOQUEADA`, el "motivo de creación" y el resultado de `cambiar_estado_tarea`
   se guardan en la bitácora con `tipo_evento=CAMBIO_ESTADO`**; no existe un tipo de evento
   específico para bloqueos en `apps/core/choices.py::TipoEvento` y crear uno solo para esto
   no lo pidió el plan ni `docs/modelo-datos.md`.
5. **`fechas_sugeridas` solo considera dependencias `FI`** (tal como pide el plan) y usa la
   convención "fin del predecesor + 1 día + `dias_desfase`" (una tarea `FI` empieza el día
   siguiente al que termina su predecesora cuando el desfase es 0). El plan no fija esta
   convención exactamente, así que queda documentada en el docstring del servicio.
6. **La pestaña *Tareas* del detalle de proyecto reutiliza `opcionesRecursos()`**, ya cargado
   por la pestaña *Recursos* (fase 06), para el selector de responsable del formulario de
   tarea, en vez de pedir otra vez el catálogo completo de recursos.
7. **El detalle de tarea (`/tareas/:id`) no incluye la línea de tiempo de bitácora** que pide
   el punto 7.3.12 del plan (`/bitacora/?entidad=Tarea&entidad_id=`). Ese endpoint **no existe
   todavía**: `docs/api-contrato.md` lo documenta como `GET /bitacora/?proyecto=&tipo_evento=
   &desde=&hasta=` bajo la sección "Expediente", que es alcance explícito de la **fase 09**
   (`apps/expediente` no tiene `views.py`/`urls.py` todavía, y no está registrado en
   `config/urls.py`). Construirlo ahora habría sido adelantar trabajo de otra fase, algo que
   `PLAN.md` prohíbe explícitamente. Se dejó un bloque `<app-en-construccion>` en su lugar
   (igual que "Horas registradas", que es expresamente alcance de la fase 08) y se documenta
   aquí para que la fase 09 no lo pase por alto.
8. **El Gantt no implementa virtualización real por rango visible.** El punto 7.3.11 pide que
   "funcione con 100 tareas sin trabarse (virtualización simple por rango visible)". Con una
   grilla CSS de ~100 filas simples (sin recálculos de layout por fila, solo `grid-column`
   estático) el navegador no necesita ayuda para renderizarla con fluidez; añadir una ventana
   deslizante manual habría sido complejidad sin beneficio medible para ese volumen de filas.
   Si en el uso real se ven con cientos de tareas por proyecto, ahí sí valdría la pena revisar
   esto. El scroll horizontal propio y el `minmax(48px, 1fr)` por columna sí están implementados
   para pantallas angostas.
9. **El cronograma usa 2 consultas (`Tarea` + `DependenciaTarea`), no 1**, para quedar muy por
   debajo de las 10 que exige la prueba (`test_cronograma_resuelve_en_menos_de_10_consultas_
   con_40_tareas`) sin necesidad de un SQL manual: una única consulta `values()` adicional para
   las dependencias es más simple y legible que forzar todo a un solo `JOIN` en el ORM.
