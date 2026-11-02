# Fase 09 — Seguimientos y expediente digital

**Rama:** `fase-09-seguimiento-expediente` · **Depende de:** fase 08 · **Esfuerzo:** 2 sesiones

## Objetivo

Cubrir los objetivos 1 y 1.5: el **seguimiento periódico** del proyecto (diario, semanal o
mensual) que se precarga con los datos reales de ejecución y se publica, y el **expediente
digital** donde queda documentado todo: seguimientos, tareas, ejecución, documentos
versionados y una línea de tiempo auditable.

## Precondiciones

- Fase 08 terminada (sin ejecución aprobada no hay nada que precargar).
- Lee `docs/modelo-datos.md` §7 y §8, y `docs/api-contrato.md` §6.

---

## Backend

### 9.1 Servicio de seguimiento

1. `apps/seguimiento/services.py`:
   - `precargar(proyecto, periodicidad, periodo_inicio)` → devuelve un **borrador sin guardar**:
     - normaliza el periodo con `apps/core/periodos.py`;
     - `horas_periodo` y `costo_periodo`: lo aprobado cuyo periodo cae dentro del rango;
     - `horas_acumuladas` y `costo_acumuladas`: desde el inicio del proyecto a `fecha_corte`;
     - `semaforo_calculado` con la tabla de `docs/modelo-datos.md` §10;
     - `avance_reportado` precargado con el del seguimiento anterior (para que el líder lo
       actualice, no lo invente desde cero);
     - además, para ayudar a redactar: listas de `tareas_completadas_en_periodo`,
       `tareas_vencidas`, `hitos_del_periodo` y `tareas_creadas_en_periodo`.
       Estas listas son informativas y **no** se guardan en el modelo.
   - `publicar(seguimiento, usuario)`, en una sola transacción:
     1. valida que esté en `BORRADOR`;
     2. exige `justificacion_semaforo` si `semaforo != semaforo_calculado`;
     3. recalcula y **congela** los cuatro campos calculados;
     4. actualiza `Proyecto.avance_reportado` y `Proyecto.semaforo`;
     5. pone `estado=PUBLICADO`, `publicado_en`, `publicado_por`;
     6. escribe `registrar_evento(tipo_evento="PUBLICACION", ...)`.
   - Un seguimiento `PUBLICADO` es inmutable (409 ante cualquier escritura). Para corregirlo se
     crea uno nuevo del mismo periodo con `periodicidad` distinta no: se habilita
     `POST /seguimientos/{id}/reabrir/` solo para `ADMIN`, que deja rastro en bitácora.
   - `marcar_compromisos_vencidos()`: comando de gestión `actualizar_compromisos` que pone
     `VENCIDO` a los `ABIERTO` con `fecha_compromiso < hoy`. Se documenta que en v1 se corre a
     mano o por tarea programada del sistema operativo (no hay Celery; está fuera de alcance).

### 9.2 Servicio de expediente

2. `apps/expediente/services.py`:
   - `guardar_documento(archivo, metadatos, usuario)`:
     - valida extensión contra `EXTENSIONES_PERMITIDAS` y tamaño contra `MAX_UPLOAD_MB`
       (`ErrorArchivo`, 413);
     - calcula `hash_sha256` leyendo por bloques (no carga el archivo entero en memoria);
     - si ya existe un documento **activo** del mismo proyecto con ese hash, responde 409
       informando cuál es, y ofrece en `detalles` el id del existente;
     - guarda en `expediente/<proyecto_id>/<uuid>.<ext>`, nunca con el nombre original
       (que se conserva en `nombre_original`);
     - sanea el `nombre_original` antes de guardarlo (quita rutas y caracteres de control);
     - escribe `registrar_evento(tipo_evento="CARGA_DOCUMENTO", ...)`.
   - `nueva_version(documento, archivo, usuario)`: crea el registro con
     `version = anterior + 1`, `documento_padre` apuntando a la raíz de la cadena, marca
     `es_version_vigente=False` en la anterior y registra `NUEVA_VERSION`.
   - `descargar(documento, usuario)`: valida permiso sobre el proyecto y devuelve
     `FileResponse` con `Content-Disposition: attachment; filename="<nombre_original>"` y
     `Content-Type` del `mime` almacenado. **Nunca** se sirve `MEDIA_ROOT` como estático.
   - `armar_expediente(proyecto)` → `{documentos_por_categoria, linea_tiempo, totales}`:
     - `documentos_por_categoria`: solo versiones vigentes, agrupadas;
     - `linea_tiempo`: mezcla de `EntradaBitacora` del proyecto, seguimientos publicados,
       hitos cumplidos o incumplidos y cargas de documentos, ordenada desc. por fecha y
       paginada;
     - `totales`: documentos, seguimientos publicados, horas y costo acumulados, tareas
       cerradas.

### 9.3 API

3. `SeguimientoViewSet` con las acciones `precargar` (POST, no guarda), `publicar`, `reabrir`;
   filtros `proyecto`, `periodicidad`, `estado`, `fecha_corte__gte/__lte`.
   Permisos: crear y editar, `LIDER` del proyecto o `PMO`; publicar, lo mismo; reabrir, `ADMIN`.
4. `CompromisoSeguimientoViewSet`: CRUD, filtros `estado`, `responsable`, `vencidos`.
5. `DocumentoExpedienteViewSet`: `POST` multipart, `nueva-version`, `descargar`,
   `DELETE` lógico. `GET /proyectos/{id}/expediente/`.
   Un `RECURSO` puede subir documentos de los proyectos donde está asignado y borrar solo los
   que él subió.
6. `BitacoraViewSet` de solo lectura con filtros `proyecto`, `tipo_evento`, `entidad`,
   `entidad_id`, `usuario`, `desde`, `hasta`.
7. `GET /proyectos/{id}/expediente/exportar/` → **PDF** del expediente con portada
   (datos del proyecto y KPIs), seguimientos publicados, resumen de tareas, resumen de
   ejecución y el índice de documentos con sus versiones.
   Genera el PDF con `reportlab` (agrégalo a las dependencias y a `docs/STACK-LOCK.md`).
   Si el PDF se complica, el criterio de aceptación admite **HTML imprimible** como
   alternativa, pero debe quedar anotado en el archivo de la fase.
8. Pruebas:
   - `precargar` suma solo lo aprobado del periodo y nada de fuera.
   - Publicar con semáforo distinto del calculado sin justificación → 400.
   - Publicar actualiza `Proyecto.avance_reportado` y `Proyecto.semaforo`.
   - Un seguimiento publicado no se puede editar (409) y sí se puede reabrir como `ADMIN`.
   - Unicidad de `(proyecto, periodicidad, periodo_inicio)`.
   - Subir un archivo con extensión no permitida → 400; uno de 30 MB con tope de 25 → 413.
   - Subir el mismo archivo dos veces → 409 con el id del existente.
   - `nueva-version` encadena versiones y deja una sola vigente.
   - La descarga de un documento de un proyecto ajeno a un `RECURSO` → 404.
   - La línea de tiempo del expediente incluye los eventos de publicación y de carga.
   - El nombre del archivo guardado **no** es el nombre original (prueba de recorrido de rutas
     con un nombre como `../../etc/passwd`).

---

## Frontend

### 9.4 Pantallas

9. `features/seguimientos/data/seguimientos.service.ts` y
   `features/expediente/data/expediente.service.ts`.
10. **Seguimientos** (`/seguimientos`): tabla multiproyecto con proyecto, periodo,
    fecha de corte, avance, semáforo, estado (borrador/publicado) y autor.
    Filtros en la URL. Botón "Nuevo seguimiento".
11. **Editor de seguimiento** (`/seguimientos/nuevo`, `/seguimientos/:id`):
    - Paso 1: proyecto, periodicidad y periodo → botón "Precargar datos", que llama a
      `precargar` y rellena la pantalla.
    - Bloque de solo lectura con los datos calculados: horas y costo del periodo, acumulados,
      % de consumo, semáforo calculado. Cada cifra con su etiqueta clara de "calculado".
    - Bloque editable: avance reportado (con el anterior visible al lado para comparar),
      semáforo declarado (`app-semaforo` seleccionable). Si el declarado difiere del calculado,
      aparece el campo "Justificación" como obligatorio, con el texto explicando por qué.
    - Cuatro áreas de texto: logros, dificultades, riesgos, acciones siguientes.
    - Panel de ayuda lateral con las listas informativas que devolvió `precargar`
      (tareas completadas, vencidas, hitos, tareas nuevas del periodo) y un botón para
      insertarlas como viñetas en "Logros".
    - Compromisos: tabla editable con descripción, responsable y fecha.
    - Adjuntos del seguimiento: carga directa al expediente con `seguimiento` ya fijado.
    - Botones "Guardar borrador" y "Publicar" (este con `app-confirmacion` que advierte que
      el seguimiento quedará inmutable y actualizará el estado del proyecto).
12. **Pestaña *Seguimientos* del proyecto**: historial en tarjetas con semáforo, avance y un
    enlace al detalle; gráfico simple de evolución del avance **pendiente** para la fase 10
    (deja el marcador).
13. **Expediente digital** (`/proyectos/:id/expediente` y pestaña homónima):
    - Cabecera con los totales.
    - **Documentos**: agrupados por categoría en `app-tabs`; tabla con nombre, versión,
      tamaño, quién subió, fecha, acciones (descargar, nueva versión, eliminar).
      Zona de arrastrar y soltar para subir, con barra de progreso real
      (`HttpClient` con `reportProgress: true`), validación de extensión y tamaño **antes**
      de enviar, y la posibilidad de subir varios archivos.
    - **Línea de tiempo**: lista vertical paginada con icono por tipo de evento, fecha, usuario
      y descripción; filtro por tipo de evento y por rango de fechas. Los cambios de estado
      muestran el diff en un desplegable ("de EJECUCION a SUSPENDIDO").
    - Botón "Exportar expediente" que descarga el PDF.
14. Las descargas pasan siempre por el endpoint autenticado: se obtiene el `Blob` con
    `HttpClient` y se entrega con `URL.createObjectURL`. **Nunca** se construye un enlace
    directo a `MEDIA_ROOT`.

---

## Criterios de aceptación

- [x] "Precargar datos" trae horas y costos reales del periodo, solo de lo aprobado.
- [x] Declarar verde cuando el cálculo da rojo exige justificación.
- [x] Al publicar, el proyecto queda con el avance y el semáforo del seguimiento.
- [x] Un seguimiento publicado no se puede editar y un `ADMIN` puede reabrirlo, con rastro.
- [x] Subir un archivo de extensión no permitida se bloquea en el cliente y en el servidor.
- [x] Subir dos veces el mismo archivo avisa que ya existe y enlaza al existente.
- [x] Una segunda versión deja la anterior accesible pero marcada como no vigente.
- [x] La descarga de un documento de otro proyecto por un `RECURSO` devuelve 404.
- [x] Un archivo llamado `../../x.pdf` se guarda con nombre seguro y se descarga con su
      nombre original saneado.
- [x] La línea de tiempo muestra creación del proyecto, cambios de estado, aprobaciones,
      publicaciones y cargas de documentos.
- [x] "Exportar expediente" produce un PDF (o HTML imprimible, si quedó anotado) legible.
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/seguimiento apps/expediente -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend python manage.py actualizar_compromisos
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Tablero global y gráficos (fase 10), firma digital de documentos, almacenamiento en S3,
notificaciones por correo, OCR de adjuntos.

## Evidencia

### Backend

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/seguimiento apps/expediente -q
.......................................................                  [100%]
55 passed in 90.73s (0:01:30)

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
......................................................                   [100%]
342 passed in 441.86s (0:07:21)

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
(sin warnings/errores; exit 0)

$ docker compose -f infra/docker-compose.yml exec backend python manage.py actualizar_compromisos
2 compromiso(s) marcado(s) como VENCIDO.
```

### Frontend

```
$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
Linting "frontend"...
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npm run build
Application bundle generation complete. [30.2s]
(chunks nuevos: editor, lista, aprobaciones ya existentes + lista/editor de
seguimientos, panel de expediente embebido en la pestaña del proyecto)

$ docker compose -f infra/docker-compose.yml exec frontend npm test -- --watch=false
Test Files  7 passed (7)
     Tests  31 passed (31)
```
(`npm test` no es un comando de verificación exigido por esta fase; se corrió para confirmar
que nada de fases anteriores se rompió — igual que en las fases 07 y 08.)

### Verificación manual contra el backend real (`seed_demo`, sin navegador disponible)

Con `admin@seguimiento.local` contra `PRY-2026-001`:

- `precargar()` sobre un periodo con registros `APROBADO`, `ENVIADO` y de otro mes confirmó
  que solo entra lo `APROBADO` y dentro del rango exacto del periodo.
- `guardar_documento` con `SimpleUploadedFile("../../etc/passwd", ...)` → `nombre_original`
  saneado a `"passwd"`; la ruta de almacenamiento ya era segura por construcción (usa un
  `uuid`, nunca el nombre original).
- Subir el mismo contenido dos veces → 409 con `detalles.documento_existente` apuntando al id
  del primero.
- `nueva_version` encadenó v1 → v2 → v3, con `documento_padre` siempre apuntando a la raíz
  (v1), no al eslabón anterior, y solo la última `es_version_vigente=True`.
- `armar_expediente` + `generar_pdf_expediente` produjeron un PDF real (`%PDF-` en los
  primeros bytes) con portada, seguimientos publicados, resumen de tareas y de ejecución, e
  índice de documentos.
- Todos los datos de prueba creados a mano se limpiaron al terminar (incluido el archivo
  físico del documento de prueba) y se restauró la contraseña del usuario admin a su estado
  inicial (inutilizable).

No hay navegador disponible en este entorno (igual que en fases 05-08): el editor de
seguimiento, la zona de arrastrar y soltar del expediente y la línea de tiempo se verificaron
por `ng build`/`ng lint` (sin errores de plantilla) y por la forma real de los datos que
consumen, no renderizados pixel a pixel en un navegador real.

### Decisiones y discrepancias documentadas

1. **Bug real encontrado y corregido: DRF trata un `BooleanField` ausente en
   `multipart/form-data` como `False`, no como "use el default del modelo".** Como
   `DocumentoExpedienteSerializer` incluía `"activo"` como campo escribible normal (igual que
   todos los demás serializers del proyecto, que nunca reciben multipart porque no suben
   archivos), cada alta de documento vía la API quedaba con `activo=False` — invisible para
   cualquier `GET`/`DELETE` posterior, incluida la propia detección de duplicados (que filtra
   `activo=True`). Se corrigió marcando `"activo"` como `read_only` en ese serializer
   específico (no hacía falta tocar los demás, que no son multipart). Se encontró al escribir
   la prueba de duplicado exacto, que fallaba con un 201 en vez de 409; queda anotado aquí
   para que no se repita si se agrega otro endpoint de subida de archivos.
2. **El duplicado exacto se detecta comparando `hash_sha256` dentro del mismo `proyecto`**
   antes de guardar: `guardar_documento` lanza `ErrorConflicto` (409) con el id y el nombre
   del documento existente en `detalles`, tal como pide el plan.
3. **`Proyecto.semaforo` se actualiza con el semáforo *declarado* del seguimiento (`seguimiento.semaforo`), no con el calculado.** `docs/modelo-datos.md` §7 dice "actualiza
   Proyecto.avance_reportado y Proyecto.semaforo" sin precisar cuál de los dos; se usó el
   declarado porque es el juicio humano del líder (respaldado por `justificacion_semaforo`
   cuando difiere del calculado) — el calculado queda disponible de todas formas en
   `semaforo_calculado`, congelado en el mismo registro.
4. **La línea de tiempo del expediente es directamente `EntradaBitacora` del proyecto**, sin
   "mezclar" manualmente seguimientos, hitos y documentos como sugiere la redacción del plan:
   las señales de auditoría (fase 02) y los `registrar_evento` explícitos (publicar, aprobar,
   cargar documento, nueva versión) ya escriben ahí todo eso. Reconstruir esas listas por
   separado habría sido trabajo duplicado sin ningún beneficio, y la prueba
   `test_linea_tiempo_incluye_publicacion_y_carga` confirma que ambos tipos de evento aparecen
   mezclados y ordenados por fecha.
5. **`BitacoraViewSet` (fase 02 lo dejó pendiente, fase 07 lo documentó como hueco) quedó
   construido en esta fase**, con los filtros de `docs/api-contrato.md` §6 y un permiso propio
   que excluye a RECURSO y CONSULTA (la matriz de §8 les da "—", a diferencia de los demás
   recursos donde CONSULTA entra en `ROLES_ALCANCE_TOTAL`). Esto cierra la referencia que
   `docs/plan/fase-07-tareas-programacion.md`'s Evidencia dejó abierta sobre el detalle de
   tarea.
6. **`armar_expediente` pagina la línea de tiempo con `pagina`/`tamano` simples (slicing en
   Python), no con el paginador estándar de DRF**, porque va embebida dentro de la respuesta
   de `/proyectos/{id}/expediente/` junto con `documentos_por_categoria` y `totales`, no como
   un listado propio de un `ViewSet`.
7. **El PDF se generó con `reportlab`** (agregado a `pyproject.toml` y a `docs/STACK-LOCK.md`,
   versión real instalada 5.1.0): no hizo falta recurrir a la alternativa de HTML imprimible
   que el criterio de aceptación permitía si esto se complicaba.
8. **El permiso de borrado de documentos para `RECURSO` sigue el texto específico de esta
   fase** ("puede borrar solo los que él mismo subió", §9.3.5) en vez de la matriz general de
   `docs/api-contrato.md` §8 (que no le da "B" a RECURSO en absoluto) — mismo criterio que en
   fases anteriores: el texto más detallado de la fase gana, y queda anotado aquí para que
   quien revise la matriz no lo lea como una contradicción sin explicación.
9. **El filtro `usuario` en `FiltroRecurso`** que la fase 08 agregó para "Mi registro de
   horas" también lo reutiliza el editor de seguimiento para resolver nombres de responsables
   de compromisos vía `UsuariosService` (ya existente desde fase 03), sin cambios adicionales
   al backend.
