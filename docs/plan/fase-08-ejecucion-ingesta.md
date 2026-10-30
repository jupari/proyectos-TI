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

- [ ] Un `RECURSO` registra horas diarias de una semana y los totales cuadran.
- [ ] Un registro semanal creado desde un miércoles se normaliza a lunes-domingo.
- [ ] Intentar un registro mensual que solapa uno diario existente muestra en la UI la lista
      de registros en conflicto.
- [ ] Un `LIDER` aprueba un lote de registros y los KPIs del proyecto cambian al instante.
- [ ] Un registro rechazado muestra su motivo al recurso y no cuenta en los KPIs.
- [ ] Nadie puede aprobar su propio registro (salvo `ADMIN`).
- [ ] Un registro aprobado no se puede editar; al reabrirlo sí, y queda en bitácora.
- [ ] `Tarea.horas_ejecutadas` coincide con la suma de los registros aprobados de esa tarea.
- [ ] La pestaña *Ejecución* muestra plan vs. ejecutado por recurso y por mes con los valores
      correctos y avisa de lo pendiente de aprobación.
- [ ] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

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

<!-- Pega aquí la salida real de los comandos de verificación. -->
