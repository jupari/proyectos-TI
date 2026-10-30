# Modelo de datos

Fuente de verdad de las entidades. **Ninguna fase puede crear un campo que no esté aquí.**
Si falta algo, se actualiza primero este documento y luego se implementa.

Convenciones de lectura:
- `PK` clave primaria, `FK` llave foránea, `U` único, `I` indexado, `C` calculado (no se escribe desde la API).
- Todos los modelos heredan de `ModeloBase` y por tanto tienen, sin repetirlo en cada tabla:

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | UUID | PK, generado por el servidor |
| `creado_en` | DateTimeField | `auto_now_add` |
| `actualizado_en` | DateTimeField | `auto_now` |
| `creado_por` | FK Usuario (null) | lo llena el middleware de auditoría |
| `actualizado_por` | FK Usuario (null) | lo llena el middleware de auditoría |
| `activo` | Boolean | default `True`; el borrado es lógico |

Decimales: dinero `max_digits=18, decimal_places=2`; horas `max_digits=10, decimal_places=2`;
porcentajes `max_digits=5, decimal_places=2` (0.00 a 100.00).

---

## 1. App `accounts`

### `Usuario` (hereda `AbstractUser`, `AUTH_USER_MODEL`)
| Campo | Tipo | Notas |
|-------|------|-------|
| `email` | Email | **U**, es el `USERNAME_FIELD`; `username` se elimina |
| `nombres` | Char(120) | |
| `apellidos` | Char(120) | |
| `nombre_completo` | property | `f"{nombres} {apellidos}"` |
| `cargo` | Char(120) | opcional |
| `telefono` | Char(40) | opcional |
| `proveedor_auth` | Char(20) | `LOCAL` \| `GOOGLE`; default `LOCAL` |
| `google_sub` | Char(64) | **U**, null; identificador estable de Google |
| `avatar_url` | URL | null; viene de Google |
| `ultimo_acceso_en` | DateTime | null |
| `debe_cambiar_clave` | Boolean | default `False`; `True` en usuarios creados por el admin |
| `is_active`, `is_staff`, `is_superuser`, `groups` | de Django | los `groups` son los roles |

Reglas:
- Un usuario con `proveedor_auth=GOOGLE` no puede autenticarse con contraseña (clave inutilizable).
- Si llega un login de Google con un `email` que ya existe como `LOCAL`, se vincula la cuenta
  (se guarda `google_sub`) y se registra en bitácora; no se crea un usuario duplicado.

### `RolMeta`
| Campo | Tipo | Notas |
|-------|------|-------|
| `grupo` | OneToOne `auth.Group` | |
| `codigo` | Char(20) | **U**; `ADMIN` \| `PMO` \| `LIDER` \| `RECURSO` \| `CONSULTA` |
| `descripcion` | Char(255) | |
| `es_sistema` | Boolean | `True` en los cinco roles sembrados; no se pueden borrar |
| `orden` | Integer | para listarlos de mayor a menor privilegio |

---

## 2. App `catalogos`

### `Area` — área o dependencia que solicita el proyecto
`codigo` Char(20) **U** · `nombre` Char(150) · `responsable` FK Usuario (null)

### `Portafolio` — agrupador de proyectos (programa, línea estratégica)
`codigo` Char(20) **U** · `nombre` Char(150) · `descripcion` Text · `responsable` FK Usuario (null)

### `PerfilRecurso` — perfil técnico con tarifa de referencia
`codigo` Char(20) **U** · `nombre` Char(120) (p. ej. "Desarrollador Senior") ·
`tarifa_hora_referencia` Decimal dinero · `moneda` Char(3) default `COP`

---

## 3. App `proyectos`

### `Proyecto`
| Campo | Tipo | Notas |
|-------|------|-------|
| `codigo` | Char(30) | **U**, **I**; p. ej. `PRY-2026-001` |
| `nombre` | Char(200) | **I** |
| `descripcion` | Text | |
| `objetivo` | Text | |
| `portafolio` | FK Portafolio | null |
| `area_solicitante` | FK Area | |
| `gerente` | FK Usuario | related_name `proyectos_como_gerente` |
| `lider_tecnico` | FK Usuario | null, related_name `proyectos_como_lider` |
| `estado` | Char(20) | `BORRADOR` \| `PLANEACION` \| `EJECUCION` \| `SUSPENDIDO` \| `CERRADO` \| `CANCELADO` |
| `prioridad` | Char(10) | `BAJA` \| `MEDIA` \| `ALTA` \| `CRITICA` |
| `fecha_inicio_plan` | Date | |
| `fecha_fin_plan` | Date | |
| `fecha_inicio_real` | Date | null |
| `fecha_fin_real` | Date | null |
| `moneda` | Char(3) | default `COP` |
| `presupuesto_horas` | Decimal horas | presupuesto aprobado en horas |
| `presupuesto_dinero` | Decimal dinero | presupuesto aprobado total en dinero |
| `avance_reportado` | Decimal % | lo declara el líder en el último seguimiento publicado |
| `semaforo` | Char(10) | **C** `VERDE` \| `AMARILLO` \| `ROJO`; ver §10 |
| `observaciones` | Text | |

Reglas:
- `fecha_fin_plan >= fecha_inicio_plan` (constraint de BD y validación en el serializer).
- Pasar a `EJECUCION` exige `fecha_inicio_real` y al menos una `AsignacionRecurso`.
- Pasar a `CERRADO` exige `fecha_fin_real` y que no queden tareas en `EN_PROGRESO`.
- Transiciones permitidas: `BORRADOR→PLANEACION→EJECUCION→{SUSPENDIDO,CERRADO}`,
  `SUSPENDIDO→EJECUCION`, cualquiera `→CANCELADO`. Otra transición devuelve 400.
- `presupuesto_dinero` debe ser ≥ la suma de `RubroPresupuesto.monto_planeado`; si no, 400.

### `FaseProyecto` — etapa del proyecto, sirve para el avance ponderado
`proyecto` FK · `nombre` Char(150) · `orden` Integer · `peso` Decimal % ·
`fecha_inicio_plan` Date · `fecha_fin_plan` Date · `fecha_inicio_real` Date null ·
`fecha_fin_real` Date null · `estado` Char(20) (`PENDIENTE` \| `EN_PROGRESO` \| `COMPLETADA`)

Reglas: `U(proyecto, orden)`. La suma de `peso` de las fases activas de un proyecto debe ser
100; se valida al guardar y el error indica cuánto falta o sobra.

### `Hito`
`proyecto` FK · `nombre` Char(200) · `descripcion` Text · `fecha_plan` Date ·
`fecha_real` Date null · `estado` Char(20) (`PENDIENTE` \| `CUMPLIDO` \| `INCUMPLIDO` \| `REPROGRAMADO`) ·
`criterio_cumplimiento` Text · `es_entregable` Boolean

### `RubroPresupuesto` — presupuesto en dinero que **no** son horas de recursos
`proyecto` FK · `categoria` Char(20) (`PERSONAL` \| `LICENCIAS` \| `INFRAESTRUCTURA` \| `SERVICIOS` \| `CAPACITACION` \| `OTROS`) ·
`descripcion` Char(255) · `monto_planeado` Decimal dinero · `monto_ejecutado` Decimal **C** (suma de `GastoEjecutado` aprobados)

---

## 4. App `recursos`

### `Recurso` — persona, proveedor o concepto consumible
| Campo | Tipo | Notas |
|-------|------|-------|
| `tipo` | Char(20) | `INTERNO` \| `CONTRATISTA` \| `PROVEEDOR` |
| `nombre` | Char(200) | **I** |
| `usuario` | FK Usuario | null; se llena si el recurso tiene cuenta para registrar sus horas |
| `perfil` | FK PerfilRecurso | null |
| `email` | Email | null |
| `capacidad_horas_mes` | Decimal horas | default 160 |
| `fecha_ingreso` | Date | null |
| `fecha_retiro` | Date | null |

Regla: si `usuario` está presente es **U**; un usuario no puede estar ligado a dos recursos.

### `TarifaRecurso` — historial de tarifas, para costear con la vigente a la fecha
`recurso` FK · `valor_hora` Decimal dinero · `moneda` Char(3) ·
`vigente_desde` Date · `vigente_hasta` Date null

Reglas:
- No se permiten rangos de vigencia solapados para el mismo recurso (constraint + validación).
- `valor_hora_vigente(recurso, fecha)` es la función única para resolver la tarifa; vive en
  `apps/recursos/services.py` y la usan la asignación y la ejecución.
- Si no hay tarifa vigente para la fecha, se cae a `perfil.tarifa_hora_referencia`; si tampoco
  hay, el registro de ejecución se rechaza con 400 y mensaje explícito.

### `AsignacionRecurso` — **el plan** de recursos del proyecto
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | |
| `recurso` | FK | |
| `fase` | FK FaseProyecto | null |
| `rol_en_proyecto` | Char(120) | texto libre: "Analista funcional" |
| `fecha_desde` | Date | |
| `fecha_hasta` | Date | |
| `porcentaje_dedicacion` | Decimal % | |
| `horas_planeadas` | Decimal horas | |
| `valor_hora_plan` | Decimal dinero | se precarga con la tarifa vigente a `fecha_desde` |
| `costo_planeado` | Decimal **C** | `horas_planeadas * valor_hora_plan` |

Reglas:
- `U(proyecto, recurso, fase, fecha_desde)`.
- El rango debe caer dentro de las fechas plan del proyecto; si no, 400.
- Advertencia (no bloqueo) si la suma de `porcentaje_dedicacion` del recurso en un mes
  supera 100: la respuesta incluye `advertencias: []`.

---

## 5. App `tareas`

### `Tarea` — tareas y actividades, se pueden agregar en cualquier momento (objetivo 1.4)
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | **I** |
| `fase` | FK FaseProyecto | null |
| `tarea_padre` | FK self | null, related_name `subtareas` |
| `codigo` | Char(30) | **U** por proyecto; autogenerado `PRY-2026-001-T015` |
| `nombre` | Char(250) | |
| `descripcion` | Text | |
| `tipo` | Char(20) | `ACTIVIDAD` \| `TAREA` \| `INCIDENCIA` \| `CAMBIO` \| `REUNION` |
| `estado` | Char(20) | `PENDIENTE` \| `EN_PROGRESO` \| `BLOQUEADA` \| `EN_REVISION` \| `COMPLETADA` \| `CANCELADA` |
| `prioridad` | Char(10) | `BAJA` \| `MEDIA` \| `ALTA` \| `CRITICA` |
| `responsable` | FK Recurso | null |
| `fecha_inicio_plan` | Date | |
| `fecha_fin_plan` | Date | |
| `fecha_inicio_real` | Date | null |
| `fecha_fin_real` | Date | null |
| `horas_estimadas` | Decimal horas | |
| `horas_ejecutadas` | Decimal **C** | suma de `RegistroEjecucion` aprobados de la tarea |
| `avance` | Decimal % | lo declara el responsable |
| `orden` | Integer | para ordenar dentro de la fase |
| `creada_durante_ejecucion` | Boolean | `True` si se creó con el proyecto ya en `EJECUCION` |
| `motivo_creacion` | Text | obligatorio si `creada_durante_ejecucion=True` |

Reglas:
- Una tarea no puede ser su propia ancestro (se valida la cadena de `tarea_padre`).
- Profundidad máxima de jerarquía: 3 niveles.
- `COMPLETADA` exige `fecha_fin_real` y fija `avance=100`.
- `avance` de una tarea con subtareas es **calculado** como el promedio ponderado por
  `horas_estimadas` de sus hijas y no se puede escribir directamente.

### `DependenciaTarea`
`tarea_origen` FK Tarea · `tarea_destino` FK Tarea ·
`tipo` Char(10) (`FI` fin-inicio \| `II` inicio-inicio \| `FF` fin-fin \| `IF` inicio-fin) ·
`dias_desfase` Integer (puede ser negativo)

Reglas: `U(tarea_origen, tarea_destino)`; ambas tareas del mismo proyecto; se rechazan ciclos
(detección por recorrido en profundidad al guardar).

---

## 6. App `ejecucion`

### `RegistroEjecucion` — ingesta de horas, diaria / semanal / mensual (objetivo 1.3)
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | **I** |
| `tarea` | FK Tarea | null (permite registrar al proyecto sin tarea) |
| `recurso` | FK Recurso | **I** |
| `periodicidad` | Char(10) | `DIARIA` \| `SEMANAL` \| `MENSUAL` |
| `periodo_inicio` | Date | **I** |
| `periodo_fin` | Date | se calcula si no se envía, según `periodicidad` |
| `horas` | Decimal horas | > 0 |
| `valor_hora_aplicado` | Decimal dinero | **C** al crear, con `valor_hora_vigente(recurso, periodo_inicio)`; queda congelado |
| `costo` | Decimal dinero | **C** `horas * valor_hora_aplicado` |
| `descripcion` | Text | qué se hizo |
| `estado_aprobacion` | Char(10) | `BORRADOR` \| `ENVIADO` \| `APROBADO` \| `RECHAZADO` |
| `motivo_rechazo` | Text | obligatorio si `RECHAZADO` |
| `aprobado_por` | FK Usuario | null |
| `aprobado_en` | DateTime | null |
| `registrado_por` | FK Usuario | quien lo capturó |

Reglas:
- Coherencia de periodo: `DIARIA` ⇒ `periodo_fin = periodo_inicio`; `SEMANAL` ⇒ lunes a
  domingo; `MENSUAL` ⇒ primer y último día del mes. Se normaliza en el serializer.
- `U(recurso, proyecto, tarea, periodicidad, periodo_inicio)` — evita el doble registro.
- **No se permiten periodos solapados del mismo recurso con distinta periodicidad** en el mismo
  proyecto (un mensual y un diario del mismo mes se contarían dos veces). Error 400 con el
  detalle de los registros en conflicto.
- Topes: `DIARIA` ≤ 24 h; `SEMANAL` ≤ 60 h; `MENSUAL` ≤ `recurso.capacidad_horas_mes * 1.5`.
  Por encima del tope: advertencia, no bloqueo.
- Solo cuenta para los KPIs lo que está en `APROBADO`. Los demás estados se muestran aparte
  como "pendiente de aprobación".
- Una vez `APROBADO` el registro es inmutable; para corregirlo hay que reabrirlo
  (`POST .../reabrir/`, solo `PMO` o `ADMIN`), lo que deja entrada en bitácora.
- La fecha del periodo debe caer dentro de las fechas del proyecto; fuera de rango, 400.

### `GastoEjecutado` — ejecución presupuestal en dinero que no son horas
`proyecto` FK · `rubro` FK RubroPresupuesto · `fecha` Date · `monto` Decimal dinero ·
`proveedor` Char(200) · `numero_documento` Char(60) · `descripcion` Text ·
`estado_aprobacion` igual que arriba · `aprobado_por` FK null · `aprobado_en` DateTime null

Reglas: el `rubro` debe pertenecer al mismo proyecto. Solo los aprobados suman al ejecutado.

---

## 7. App `seguimiento`

### `Seguimiento` — reporte periódico de avance (objetivo 1 y 1.3)
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | **I** |
| `periodicidad` | Char(10) | `DIARIA` \| `SEMANAL` \| `MENSUAL` |
| `periodo_inicio` | Date | |
| `periodo_fin` | Date | |
| `fecha_corte` | Date | |
| `avance_reportado` | Decimal % | |
| `semaforo` | Char(10) | `VERDE` \| `AMARILLO` \| `ROJO`, declarado por el líder |
| `semaforo_calculado` | Char(10) | **C**, según §10; si difiere del declarado se exige `justificacion_semaforo` |
| `justificacion_semaforo` | Text | |
| `logros` | Text | |
| `dificultades` | Text | |
| `riesgos` | Text | |
| `acciones_siguientes` | Text | |
| `horas_periodo` | Decimal **C** | horas aprobadas del periodo |
| `costo_periodo` | Decimal **C** | costo aprobado del periodo |
| `horas_acumuladas` | Decimal **C** | desde el inicio del proyecto hasta `fecha_corte` |
| `costo_acumulado` | Decimal **C** | ídem |
| `estado` | Char(10) | `BORRADOR` \| `PUBLICADO` |
| `publicado_en` | DateTime | null |
| `publicado_por` | FK Usuario | null |

Reglas:
- `U(proyecto, periodicidad, periodo_inicio)`.
- Al **publicar** (`POST .../publicar/`): se congelan los cuatro campos calculados, se
  actualiza `Proyecto.avance_reportado` y `Proyecto.semaforo`, y se crea una
  `EntradaBitacora` en el expediente. Un seguimiento publicado ya no se edita.
- Solo `LIDER` del proyecto, `PMO` o `ADMIN` pueden publicar.

### `CompromisoSeguimiento`
`seguimiento` FK · `descripcion` Text · `responsable` FK Usuario · `fecha_compromiso` Date ·
`estado` Char(15) (`ABIERTO` \| `CUMPLIDO` \| `VENCIDO` \| `CANCELADO`) · `fecha_cumplimiento` Date null

Regla: un job o un `property` marca `VENCIDO` cuando `fecha_compromiso < hoy` y sigue `ABIERTO`.

---

## 8. App `expediente`

### `DocumentoExpediente` — archivos del expediente digital (objetivo 1.5)
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | **I** |
| `seguimiento` | FK Seguimiento | null; ancla el documento a un seguimiento |
| `tarea` | FK Tarea | null; ancla el documento a una tarea |
| `categoria` | Char(20) | `ACTA` \| `INFORME` \| `CONTRATO` \| `DISENO` \| `EVIDENCIA` \| `SOPORTE` \| `OTRO` |
| `nombre` | Char(250) | nombre visible |
| `archivo` | FileField | ruta `expediente/<proyecto_id>/<uuid>.<ext>` |
| `nombre_original` | Char(250) | |
| `mime` | Char(120) | |
| `tamano_bytes` | BigInteger | |
| `hash_sha256` | Char(64) | **I**; detecta duplicados exactos |
| `version` | Integer | default 1 |
| `documento_padre` | FK self | null; versiones anteriores del mismo documento |
| `es_version_vigente` | Boolean | solo una `True` por cadena de versiones |
| `descripcion` | Text | |

Reglas:
- Validación de extensión contra `EXTENSIONES_PERMITIDAS` y de tamaño contra `MAX_UPLOAD_MB`.
- Subir una nueva versión (`POST .../{id}/nueva-version/`) crea un registro con
  `version = anterior + 1`, apunta `documento_padre` y marca la anterior `es_version_vigente=False`.
- El borrado es siempre lógico: un documento del expediente nunca se elimina físicamente.
- La descarga pasa por un endpoint propio que valida permisos; **nunca** se expone la ruta de
  `MEDIA_ROOT` directamente.

### `EntradaBitacora` — línea de tiempo y auditoría del expediente
| Campo | Tipo | Notas |
|-------|------|-------|
| `proyecto` | FK | **I**; null solo para eventos no ligados a proyecto |
| `tipo_evento` | Char(30) | `CREACION` \| `ACTUALIZACION` \| `CAMBIO_ESTADO` \| `APROBACION` \| `RECHAZO` \| `PUBLICACION` \| `CARGA_DOCUMENTO` \| `NUEVA_VERSION` \| `LOGIN` \| `ASIGNACION` |
| `entidad` | Char(60) | nombre del modelo afectado |
| `entidad_id` | UUID | |
| `descripcion` | Char(500) | legible por humanos, en español |
| `datos_antes` | JSON | null |
| `datos_despues` | JSON | null |
| `usuario` | FK Usuario | null |
| `ocurrido_en` | DateTime | **I** |

Reglas: se escribe desde señales (`post_save`, `post_delete`) y desde los servicios de
aprobación y publicación. Es **solo lectura** desde la API. No se borra nunca.

---

## 9. App `tablero` — sin tablas propias

Solo lectura y agregación sobre lo anterior. Los cálculos viven en
`apps/tablero/services.py` y se reutilizan desde los serializers de proyecto y seguimiento,
para que no haya dos fórmulas distintas en el código.

---

## 10. Fórmulas de control (única definición válida)

A una `fecha_corte` dada, para un proyecto:

```
horas_planeadas   = suma(AsignacionRecurso.horas_planeadas)        # del proyecto
horas_ejecutadas  = suma(RegistroEjecucion.horas)  donde estado_aprobacion = APROBADO
costo_planeado    = suma(AsignacionRecurso.costo_planeado) + suma(RubroPresupuesto.monto_planeado)
costo_ejecutado   = suma(RegistroEjecucion.costo) + suma(GastoEjecutado.monto)   # solo APROBADO

pct_horas   = horas_ejecutadas  / horas_planeadas  * 100     # 0 si el divisor es 0
pct_dinero  = costo_ejecutado   / costo_planeado   * 100
pct_tiempo  = dias_transcurridos / dias_totales_plan * 100   # acotado a [0, 100]
avance      = Proyecto.avance_reportado

# Índices tipo valor ganado, simplificados
SPI = avance / pct_tiempo                       # >=1 en tiempo, <1 atrasado
CPI = (avance/100 * costo_planeado) / costo_ejecutado   # >=1 eficiente, <1 sobrecosto
desviacion_presupuestal = costo_ejecutado - (avance/100 * costo_planeado)
```

Semáforo calculado (se evalúa en orden, el primero que aplica gana):

| Condición | Semáforo |
|-----------|----------|
| `pct_dinero > 100` o `pct_horas > 110` o hitos incumplidos > 0 | `ROJO` |
| `avance < pct_tiempo - 15` o `CPI < 0.85` o `SPI < 0.85` | `ROJO` |
| `avance < pct_tiempo - 5` o `CPI < 0.95` o `pct_dinero > 90` | `AMARILLO` |
| en otro caso | `VERDE` |

Todos los divisores se protegen: si el denominador es 0, el indicador se devuelve como `null`
y la UI muestra un guion, **no** un 0% engañoso.

---

## 11. Índices y rendimiento

Crear explícitamente en las migraciones:
- `RegistroEjecucion`: índice compuesto `(proyecto, periodo_inicio)`, `(recurso, periodo_inicio)`,
  `(estado_aprobacion,)`.
- `Tarea`: `(proyecto, estado)`, `(responsable, estado)`.
- `Seguimiento`: `(proyecto, fecha_corte)`.
- `EntradaBitacora`: `(proyecto, ocurrido_en)`.
- Los listados de proyecto usan `select_related` para FK y `prefetch_related` para inversas;
  los KPIs se calculan con `annotate` + `Sum`, **nunca** iterando en Python.

---

## 12. Datos de demostración (`seed_demo`, fase 01)

Comando `python manage.py seed_demo` idempotente que crea: 5 usuarios (uno por rol),
3 áreas, 2 portafolios, 6 perfiles, 8 recursos con tarifas vigentes, 4 proyectos en distintos
estados (uno en rojo por sobrecosto, uno en verde, uno cerrado, uno en borrador), con fases,
hitos, rubros, asignaciones, ~40 tareas, ~120 registros de ejecución de los últimos 3 meses en
distintas periodicidades, 6 seguimientos publicados y 10 documentos de expediente de ejemplo.
