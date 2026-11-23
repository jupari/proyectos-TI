# Fase 14 — Importación de tareas, historias de usuario y sprints desde Jira

**Depende de:** fase 12 (cliente de Jira y mapeo `clave_jira`) · **Esfuerzo:** 4-6 sesiones

## Objetivo

El equipo técnico trabaja en Jira. En vez de pedirle que reporte avance en esta aplicación,
se **importan** sus tareas, historias de usuario (HU) y sprints, y el avance del proyecto se
calcula con eso. La gerencia sigue viendo el tablero; el equipo técnico no captura nada doble.
La importación es **de solo lectura y en una dirección** (Jira → aplicación), como la de horas.

## Decisiones tomadas

- Se estima en **horas** (no en puntos de historia): `Tarea.horas_estimadas` sale de la
  estimación original de Jira.
- Se usan **épicas** y se muestran: se guardan en `epica_clave` / `epica_nombre` de la tarea.
  No crean fases (la fase tiene peso y fechas propias); se pueden asociar a mano después.
- Proyecto **piloto**: `PDTIRD — 202303`. Se confirma su clave real en la lista de proyectos de
  Jira antes de mapearlo.
- Los estados de los flujos de Jira **no se conocen todavía**: la simulación de la importación
  debe listar los estados que encuentre, para configurar la tabla de traducción con datos reales.

## Traducción Jira → aplicación

| En Jira | En la aplicación |
|---|---|
| Proyecto | `Proyecto` (por `clave_jira`, ya existe) |
| Historia de usuario | `Tarea` con `tipo=HISTORIA` |
| Tarea / bug / subtarea | `Tarea` hija de su historia (`tarea_padre`); bug → `INCIDENCIA` |
| Sprint | `Sprint` (nuevo) y `Tarea.sprint` |
| Épica | `Tarea.epica_clave` y `Tarea.epica_nombre` |
| Responsable | `Recurso` por `jira_account_id` (mismo mapeo de las horas) |
| Estado | `EstadoTarea` por **categoría** de Jira: Por hacer → Pendiente, En curso → En progreso, Listo → Completada; «Bloqueado» y «En revisión» por tabla configurable según el nombre del estado |

## Avance

- **Tarea:** 0 % pendiente, 100 % completada; en curso = `timespent / estimación original`, con
  tope en 90 %.
- **Historia:** promedio de sus hijas ponderado por horas estimadas.
- **Proyecto:** `avance_reportado` pasa a calcularse desde las tareas; la gerencia puede
  ajustarlo indicando el motivo. Con eso SPI, CPI y el semáforo se alimentan solos.

## Sincronización

- Idempotente por clave de Jira (`Tarea.clave_jira` y `Sprint(proyecto, id_jira)`), reutilizando
  y **reactivando** registros borrados lógicamente (mismo fallo que hubo con las horas).
- Incremental: `updated >= última sincronización`.
- Botón en Admin → Integraciones con **simulación previa**, y luego tarea programada. La
  importación manual debe correr como trabajo asíncrono (el plan gratuito de Render corta
  peticiones largas).
- Resultado visible: creados, actualizados y errores con proyecto, clave de Jira y motivo.
- Jira manda en estado, sprint, responsable y estimación. La aplicación conserva fase,
  dependencias y observaciones.

## Fases de entrega

1. **Base** *(hecha)*: tipo `HISTORIA`, modelo `Sprint`, campos `sprint`, `epica_clave` y
   `epica_nombre` en la tarea, migración, serializadores y pruebas.
2. **Cliente Jira**: leer incidencias por JQL y sprints (API Agile); importación simulada de
   solo lectura que liste los estados encontrados.
3. **Importación real**: jerarquía historia → tareas, tabla de estados, responsables, fechas.
4. **Avance calculado** y conexión con el semáforo.
5. **Tablero**: burndown por sprint, velocidad y vista de solo lectura «Mi trabajo».
6. **Programación automática** y trabajo asíncrono.

## Riesgos

- **Fechas:** `Tarea` exige fechas de inicio y fin y se validan contra el proyecto (ya falló así
  con las horas). Hay que decidir su origen (fechas del sprint, `duedate`) y qué hacer con las
  tareas fuera del rango.
- **Permisos del token:** además de Tempo, necesita leer Jira Software (incidencias y sprints).
- **Estimaciones incompletas:** sin estimación original el avance ponderado se degrada.
- **Carga inicial:** limitarla por fecha o por sprint para no traer historial antiguo.
