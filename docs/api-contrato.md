# Contrato de API

Prefijo único: `/api/v1/`. Autenticación: `Authorization: Bearer <access_token>` salvo en
los endpoints marcados como públicos. Todas las respuestas son JSON UTF-8.

---

## 1. Convenciones de listados

Todo endpoint de lista acepta:

| Parámetro | Ejemplo | Efecto |
|-----------|---------|--------|
| `page`, `page_size` | `?page=2&page_size=50` | paginación (máx. 200) |
| `search` | `?search=portal` | busca en los campos declarados en `search_fields` |
| `ordering` | `?ordering=-fecha_fin_plan` | orden; `-` descendente |
| `activo` | `?activo=false` | por defecto solo devuelve `activo=true` |

Respuesta de lista:

```json
{
  "count": 134,
  "next": "http://localhost:8000/api/v1/proyectos/?page=3",
  "previous": "http://localhost:8000/api/v1/proyectos/?page=1",
  "results": [ ... ]
}
```

---

## 2. Autenticación y sesión (fase 03)

| Método | Ruta | Público | Descripción |
|--------|------|---------|-------------|
| POST | `/auth/login/` | sí | `{email, password}` → `{access, refresh, usuario}` |
| POST | `/auth/refresh/` | sí | `{refresh}` → `{access, refresh}` (rotación activa) |
| POST | `/auth/logout/` | no | `{refresh}` → 204, deja el refresh en la blacklist |
| GET | `/auth/yo/` | no | usuario actual con `roles`, `permisos_ui` y `proyectos_liderados` |
| PATCH | `/auth/yo/` | no | actualiza `nombres`, `apellidos`, `cargo`, `telefono` |
| POST | `/auth/cambiar-clave/` | no | `{clave_actual, clave_nueva}` |
| GET | `/auth/google/autorizar/` | sí | → `{url_autorizacion, state}` para el flujo con PKCE |
| POST | `/auth/google/callback/` | sí | `{code, state, code_verifier}` → igual que `/auth/login/` |

`usuario` en las respuestas de login:

```json
{
  "id": "…", "email": "ana@empresa.com", "nombres": "Ana", "apellidos": "Ruiz",
  "cargo": "Líder de proyecto", "avatar_url": null, "proveedor_auth": "LOCAL",
  "debe_cambiar_clave": false,
  "roles": ["LIDER"],
  "permisos_ui": ["proyectos.ver", "proyectos.editar", "ejecucion.aprobar"]
}
```

`permisos_ui` es una lista plana de cadenas que el frontend usa para mostrar u ocultar
acciones. **No es el control de acceso real**: el backend siempre revalida.

---

## 3. Catálogos y administración (fase 04 y 05)

CRUD estándar (`GET` lista, `POST`, `GET {id}`, `PATCH {id}`, `DELETE {id}` lógico) en:

- `/usuarios/` — solo `ADMIN`. Extra: `POST /usuarios/{id}/activar/`, `POST /usuarios/{id}/desactivar/`, `POST /usuarios/{id}/asignar-roles/` con `{codigos: ["LIDER"]}`
- `/roles/` — lectura para todos los autenticados, escritura solo `ADMIN`; los `es_sistema` no se borran
- `/areas/`, `/portafolios/`, `/perfiles-recurso/` — escritura `ADMIN` y `PMO`

---

## 4. Proyectos (fase 05)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/proyectos/` | filtros: `estado`, `prioridad`, `portafolio`, `area_solicitante`, `gerente`, `lider_tecnico`, `semaforo`, `fecha_inicio_plan__gte`, `fecha_fin_plan__lte`, `mis_proyectos=true` |
| POST | `/proyectos/` | crea en estado `BORRADOR` |
| GET | `/proyectos/{id}/` | incluye `resumen_ejecucion` (bloque de §10) |
| PATCH | `/proyectos/{id}/` | |
| DELETE | `/proyectos/{id}/` | lógico; rechazado si tiene ejecución aprobada |
| POST | `/proyectos/{id}/cambiar-estado/` | `{estado, observacion}`; valida la transición |
| GET | `/proyectos/{id}/resumen/` | KPIs del proyecto (§10) |
| GET | `/proyectos/{id}/fases/` | lista anidada |
| GET | `/proyectos/{id}/hitos/` | |
| GET | `/proyectos/{id}/rubros/` | |

Sub-recursos con CRUD propio, filtrables por `?proyecto=`:
`/fases-proyecto/`, `/hitos/`, `/rubros-presupuesto/`.

---

## 5. Recursos, asignación, tareas (fases 06 y 07)

- `/recursos/` — filtros `tipo`, `perfil`, `activo`, `sin_asignacion=true`
- `/recursos/{id}/tarifas/` y CRUD en `/tarifas-recurso/`
- `/recursos/{id}/carga/?desde=&hasta=` → dedicación y horas por mes del recurso
- `/asignaciones/` — filtros `proyecto`, `recurso`, `fase`; la respuesta de escritura puede
  traer `advertencias: ["El recurso queda al 130% en 2026-03"]`
- `/tareas/` — filtros `proyecto`, `fase`, `estado`, `tipo`, `prioridad`, `responsable`,
  `tarea_padre`, `vencidas=true`, `creada_durante_ejecucion=true`
- `POST /tareas/` · `PATCH /tareas/{id}/` · `POST /tareas/{id}/cambiar-estado/`
- `GET /tareas/arbol/?proyecto={id}` → jerarquía anidada lista para pintar
- `/dependencias-tarea/` — CRUD; rechaza ciclos con 409 (`CONFLICTO`) y la ruta completa del
  ciclo en `detalles.ciclo` (p. ej. `["T001", "T004", "T009", "T001"]`), que es lo que hace
  útil el error; también rechaza con 400 si las dos tareas no son del mismo proyecto
- `GET /proyectos/{id}/cronograma/` → filas con `{tarea, inicio, fin, avance, dependencias}`
  ordenadas por fase y fecha, para el diagrama de la fase 07

---

## 6. Ejecución, seguimiento y expediente (fases 08 y 09)

**Ejecución**
- `/registros-ejecucion/` — filtros `proyecto`, `tarea`, `recurso`, `periodicidad`,
  `estado_aprobacion`, `periodo_inicio__gte`, `periodo_fin__lte`, `mis_registros=true`, `origen`
  (`MANUAL`\|`JIRA`, fase 12); `origen` e `id_externo` son de solo lectura, los escribe solo la
  importación (`python manage.py importar_horas_jira`, docs/modelo-datos.md §6)
- `POST /registros-ejecucion/` · `PATCH` solo si está en `BORRADOR` o `RECHAZADO`
- `POST /registros-ejecucion/lote/` — carga varios de una vez: `{registros: [...]}` →
  `{creados: n, errores: [{indice, detalle}]}`; **no es atómico por registro**, los válidos entran
- `POST /registros-ejecucion/{id}/enviar/` — `BORRADOR` → `ENVIADO`
- `POST /registros-ejecucion/{id}/aprobar/` — `PMO`, `ADMIN` o `LIDER` del proyecto
- `POST /registros-ejecucion/{id}/rechazar/` — `{motivo_rechazo}` obligatorio
- `POST /registros-ejecucion/{id}/reabrir/` — solo `PMO` y `ADMIN`
- `GET /registros-ejecucion/resumen/?proyecto=&agrupar_por=recurso|tarea|mes` → agregados
- `/gastos-ejecutados/` — mismo ciclo de aprobación
- `GET /integraciones/jira/proyectos/` (fase 12, solo `ADMIN`/`PMO`) → lista en vivo
  `[{clave, nombre}]` de los proyectos del Jira configurado, para elegir a mano cuál corresponde
  a `Proyecto.clave_jira` en el formulario de proyecto (nunca se escribe esa clave a mano)
- `/configuracion-importacion-jira/` (fase 12, solo `ADMIN`) — `GET`/`PATCH` sobre la única fila
  de `ConfiguracionImportacionJira` (`{auto_aprobar_importados}`), sin `{id}` en la ruta
- `POST /integraciones/jira/importar/` (fase 12 adenda, solo `ADMIN`) — `{desde, hasta, dry_run?,
  auto_aprobar?}` → dispara `importar_horas_jira` sin pasar por la terminal; `auto_aprobar`, si se
  envía, decide la aprobación **solo para esa corrida** sin tocar `ConfiguracionImportacionJira`;
  si se omite, usa el valor global. Devuelve el mismo resumen que el comando
  (`{creados, actualizados, detalle: [{fecha, recurso_nombre, proyecto_codigo,
  proyecto_nombre, horas, accion}], omitidos, errores}`)
- `GET /integraciones/jira/personas-sin-mapear/?desde=&hasta=` (fase 12 adenda, solo
  `ADMIN`/`PMO`) → `[{jira_account_id, nombre, worklogs}]` de las cuentas de Jira con worklogs en
  el rango que no resuelven a ningún `Recurso` (ni por correo ni por `jira_account_id` ya
  mapeado); se asocian a mano con `PATCH /recursos/{id}/ {jira_account_id}` (docs/modelo-datos.md
  §4)

**Seguimiento**
- `/seguimientos/` — filtros `proyecto`, `periodicidad`, `estado`, `fecha_corte__gte`
- `POST /seguimientos/precargar/` — `{proyecto, periodicidad, periodo_inicio}` → devuelve un
  borrador con los cálculos del periodo ya resueltos, **sin guardar**
- `POST /seguimientos/{id}/publicar/` — congela los calculados y escribe en bitácora
- `/compromisos-seguimiento/` — CRUD, filtro `seguimiento`, `estado`, `responsable`, `vencidos=true`
- `POST /compromisos-seguimiento/{id}/convertir-tarea/` — `{horas_estimadas, fecha_inicio_plan?,
  fecha_fin_plan?, responsable?, fase?}` → crea una tarea en el cronograma del proyecto y la
  enlaza; al completarla, el compromiso se cierra solo (docs/modelo-datos.md §7)

**Expediente**
- `GET /proyectos/{id}/expediente/` → `{documentos_por_categoria, linea_tiempo, totales}`
- `/documentos-expediente/` — `POST` multipart (`archivo`, `proyecto`, `categoria`, `nombre`,
  `descripcion`, opcional `seguimiento` o `tarea`)
- `POST /documentos-expediente/{id}/nueva-version/` — multipart con `archivo`
- `GET /documentos-expediente/{id}/descargar/` → stream con `Content-Disposition`
- `GET /bitacora/?proyecto=&tipo_evento=&desde=&hasta=` — solo lectura, paginada

---

## 7. Tablero (fase 10)

| Ruta | Devuelve |
|------|----------|
| `GET /tablero/resumen/` | tarjetas globales: proyectos por estado, por semáforo, totales de horas y dinero plan vs. ejecutado, número de proyectos en riesgo |
| `GET /tablero/proyectos/` | una fila por proyecto con los KPIs de §10, filtrable igual que `/proyectos/` |
| `GET /tablero/ejecucion-mensual/?proyecto=&desde=&hasta=` | serie mensual `[{mes, horas_plan, horas_ejec, costo_plan, costo_ejec}]` |
| `GET /tablero/proyectos-por-periodo/?desde=&hasta=` (adenda) | una fila por proyecto con `{id, codigo, nombre, horas_plan, horas_ejec, pct_horas}` dentro de `[desde, hasta]` (una semana o un mes elegidos a mano, sin partir en meses calendario como `ejecucion-mensual`), más una fila `totales` con la suma; `desde`/`hasta` obligatorios |
| `GET /tablero/recursos/?desde=&hasta=` | horas planeadas vs. ejecutadas por recurso y su % de ocupación |
| `GET /tablero/tareas/?proyecto=` | conteo por estado, tareas vencidas, tareas creadas durante la ejecución |
| `GET /tablero/exportar/?formato=csv&vista=proyectos\|recursos\|ejecucion-mensual\|proyectos-por-periodo` | descarga CSV de la vista indicada |

Bloque `resumen_ejecucion` que se reutiliza en varias respuestas:

```json
{
  "fecha_corte": "2026-10-30",
  "horas_planeadas": "1200.00", "horas_ejecutadas": "860.50", "pct_horas": 71.71,
  "costo_planeado": "180000000.00", "costo_ejecutado": "142300000.00", "pct_dinero": 79.06,
  "pct_tiempo": 82.35, "avance": "70.00",
  "spi": 0.85, "cpi": 0.885, "desviacion_presupuestal": "16300000.00",
  "semaforo": "AMARILLO",
  "horas_pendientes_aprobacion": "42.00",
  "hitos_cumplidos": 3, "hitos_incumplidos": 1,
  "tareas_abiertas": 12, "tareas_vencidas": 2
}
```

---

## 8. Permisos por recurso

`L` lista/lectura · `C` crear · `E` editar · `B` borrar (lógico) · `A` aprobar/publicar ·
`—` sin acceso · `*propios*` solo sobre lo que le pertenece.

| Recurso | ADMIN | PMO | LIDER | RECURSO | CONSULTA |
|---------|-------|-----|-------|---------|----------|
| usuarios, roles | L C E B | L | — | — | — |
| catálogos | L C E B | L C E | L | L | L |
| proyectos | L C E B | L C E | L E *propios* | L *asignados* | L |
| fases, hitos, rubros | L C E B | L C E | L C E *propios* | L | L |
| recursos, tarifas | L C E B | L C E | L | L | L |
| asignaciones | L C E B | L C E | L C E *propios* | L *propias* | L |
| tareas | L C E B | L C E | L C E *propios* | L C E *propias* | L |
| registros de ejecución | L C E B A | L C E A | L C E A *propios* | L C E *propios* | L |
| gastos ejecutados | L C E B A | L C E A | L C *propios* | — | L |
| seguimientos | L C E B A | L C E A | L C E A *propios* | L | L |
| documentos del expediente | L C E B | L C E | L C E *propios* | L C *propios* | L |
| bitácora | L | L | L *propios* | — | — |
| tablero | L | L | L | L *asignados* | L |

Implementación: una clase de permiso por patrón en `apps/core/permissions.py`
(`EsAdmin`, `EsPmoOAdmin`, `EsLiderDelProyecto`, `EsDuenoDelRegistro`, `SoloLectura`) más
`get_queryset()` filtrado por rol en cada `ViewSet`. **Las dos capas son obligatorias**: un
permiso que solo cubra el detalle deja fugas en los listados.

---

## 9. Errores

Formato único, producido por un `exception_handler` propio en `apps/core/exceptions.py`:

```json
{
  "error": {
    "codigo": "VALIDACION",
    "mensaje": "No se pudo guardar el registro de ejecución.",
    "detalles": {
      "horas": ["Las horas deben ser mayores que cero."],
      "periodo_inicio": ["Ya existe un registro para este recurso en el periodo."]
    },
    "traza_id": "9f2c…"
  }
}
```

| HTTP | `codigo` | Cuándo |
|------|----------|--------|
| 400 | `VALIDACION` | datos inválidos o regla de negocio incumplida |
| 401 | `NO_AUTENTICADO` | token ausente, inválido o expirado |
| 403 | `SIN_PERMISO` | autenticado pero sin permiso sobre el recurso |
| 404 | `NO_ENCONTRADO` | no existe o está fuera del alcance del rol |
| 409 | `CONFLICTO` | transición de estado no permitida, duplicado, ciclo de dependencias |
| 413 | `ARCHIVO_GRANDE` | supera `MAX_UPLOAD_MB` |
| 422 | `REGLA_NEGOCIO` | solapamiento de periodos, suma de pesos distinta de 100 |
| 500 | `ERROR_INTERNO` | el `mensaje` es genérico; el detalle solo va al log con la `traza_id` |

El frontend muestra `error.mensaje` en el toast y pinta `error.detalles` campo por campo en
el formulario. `traza_id` se muestra en pequeño para poder rastrear el error en los logs.

---

## 10. Documentación generada

`drf-spectacular` expone:
- `/api/schema/` — OpenAPI 3 en YAML
- `/api/schema/swagger/` — Swagger UI
- `/api/schema/redoc/` — ReDoc

Toda acción personalizada (`@action`) debe llevar `@extend_schema` con `summary`,
`description`, `request` y `responses`. Un endpoint sin documentar no cierra la fase.
