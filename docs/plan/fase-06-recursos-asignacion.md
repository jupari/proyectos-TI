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

- [ ] Crear una tarifa con fecha que solapa la anterior la cierra sola y no deja huecos.
- [ ] Un recurso sin tarifa ni perfil produce un error con mensaje accionable al asignarlo.
- [ ] `GET /recursos/{id}/carga/` reparte bien las horas de una asignación que cruza meses.
- [ ] Asignar un recurso al 60% en dos proyectos del mismo mes devuelve advertencia y guarda.
- [ ] Asignar con fechas fuera del rango del proyecto se rechaza.
- [ ] El `costo_planeado` del proyecto en la pestaña *Resumen* coincide con la suma de las
      asignaciones más los rubros.
- [ ] Un `LIDER` asigna recursos en su proyecto y recibe 403 en uno ajeno.
- [ ] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

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

<!-- Pega aquí la salida real de los comandos de verificación. -->
