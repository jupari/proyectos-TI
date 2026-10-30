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

- [ ] Se puede crear una tarea en un proyecto en `EJECUCION` y queda marcada como alcance
      adicional con su motivo.
- [ ] La jerarquía admite 3 niveles y rechaza el cuarto con mensaje claro.
- [ ] El avance de una tarea padre se recalcula al cambiar el de una hija.
- [ ] Una dependencia circular se rechaza mostrando la ruta del ciclo en la UI.
- [ ] Un `RECURSO` ve y edita solo sus tareas; no puede reasignarlas.
- [ ] El cronograma dibuja plan, avance y real de un proyecto de `seed_demo` y funciona en
      pantalla de 400px de ancho con scroll horizontal.
- [ ] `/proyectos/{id}/cronograma/` cumple el límite de consultas de la prueba.
- [ ] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

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

<!-- Pega aquí la salida real de los comandos de verificación. -->
