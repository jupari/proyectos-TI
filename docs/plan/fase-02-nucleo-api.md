# Fase 02 — Núcleo de la API

**Rama:** `fase-02-nucleo-api` · **Depende de:** fase 01 · **Esfuerzo:** 1 sesión

## Objetivo

Construir la infraestructura transversal que **todas** las fases siguientes van a reutilizar:
paginación, filtros, formato de error, serializers base, auditoría automática, bitácora y
documentación OpenAPI. Si esta fase queda bien, las fases 05 a 10 son casi mecánicas.

## Precondiciones

- Fase 01 terminada, con `seed_demo` cargando datos.
- Lee `docs/api-contrato.md` §1, §8 y §9 antes de empezar.

---

## Pasos

### 2.1 Paginación y respuesta de lista

1. `apps/core/pagination.py`: `PaginacionEstandar(PageNumberPagination)` con
   `page_size = 25`, `page_size_query_param = "page_size"`, `max_page_size = 200`.
   Su `get_paginated_response` devuelve exactamente la forma de `docs/api-contrato.md` §1.
2. Regístrala como `DEFAULT_PAGINATION_CLASS` en `base.py`.

### 2.2 Formato de error único

3. `apps/core/exceptions.py`:
   - Excepciones propias: `ErrorReglaNegocio` (422, código `REGLA_NEGOCIO`),
     `ErrorConflicto` (409, `CONFLICTO`), `ErrorArchivo` (413, `ARCHIVO_GRANDE`).
   - `manejador_excepciones(exc, context)` que envuelve **toda** respuesta de error en la
     estructura de `docs/api-contrato.md` §9, incluida la de `ValidationError` de DRF y la de
     `IntegrityError` de la base de datos.
   - Genera `traza_id` con `uuid4().hex[:12]`, lo incluye en la respuesta y lo escribe en el
     log junto con la traza completa y el usuario.
   - Traduce los nombres de constraint de Postgres a mensajes en español mediante un
     diccionario `MENSAJES_CONSTRAINT` (por eso la fase 01 les puso nombres descriptivos).
     Un constraint sin traducción cae a un mensaje genérico, nunca al texto crudo de Postgres.
4. Prueba: un `POST` inválido a cualquier endpoint devuelve el sobre `{"error": {...}}` con
   `codigo`, `mensaje`, `detalles` y `traza_id`.

### 2.3 Serializers y ViewSets base

5. `apps/core/serializers.py`:
   - `SerializerBase(ModelSerializer)` con `creado_en`, `actualizado_en`, `creado_por_nombre`,
     `actualizado_por_nombre` como `read_only`, y los campos calculados siempre `read_only`.
   - `SerializerAuditoria` mixin que expone `creado_por_nombre` vía `SerializerMethodField`.
6. `apps/core/views.py`:
   - `ViewSetBase(ModelViewSet)` que:
     - usa `PaginacionEstandar`;
     - monta `DjangoFilterBackend`, `SearchFilter` y `OrderingFilter`;
     - en `perform_destroy` hace **borrado lógico** (`activo=False`) en lugar de `delete()`;
     - filtra por `activo=True` salvo que llegue `?activo=false`;
     - define `get_serializer_class()` que escoge entre el serializer de lectura y el de
       escritura según la acción (`list`/`retrieve` vs. el resto).
   - `ViewSetSoloLectura(ReadOnlyModelViewSet)` equivalente para bitácora y tablero.
7. `apps/core/filters.py`: `FiltroBase(django_filters.FilterSet)` con los filtros de rango de
   fecha reutilizables (`desde`, `hasta`) y un `BooleanFilter` para `activo`.

### 2.4 Auditoría automática

8. `apps/core/middleware.py`: `MiddlewareUsuarioActual` que guarda el usuario de la petición
   en un `contextvars.ContextVar`. **Usa `contextvars`, no variables de módulo**, para que sea
   seguro con concurrencia.
9. `apps/core/signals.py`:
   - `pre_save` sobre todo modelo que herede de `ModeloBase`: llena `creado_por` en la creación
     y `actualizado_por` en cada guardado, con el usuario del contexto.
   - `post_save` y `post_delete`: crea `EntradaBitacora` con `tipo_evento` `CREACION` o
     `ACTUALIZACION`, la entidad, el id, una descripción en español y el diff en
     `datos_antes` / `datos_despues`.
   - El diff se calcula comparando con el estado previo cargado en `pre_save`; solo incluye los
     campos que cambiaron y **excluye** `actualizado_en`, `actualizado_por` y campos de archivo.
   - Lista de modelos excluidos de la bitácora: `EntradaBitacora` (evita recursión) y los
     modelos de `token_blacklist`.
   - Resolución del `proyecto` de la entrada: si el modelo tiene un campo `proyecto` lo usa; si
     tiene una ruta indirecta (`tarea.proyecto`, `seguimiento.proyecto`, `rubro.proyecto`) la
     resuelve con un mapa explícito `RUTA_A_PROYECTO` en `apps/core/signals.py`.
10. Conecta las señales en el `ready()` del `AppConfig` de `core`.
11. Función `registrar_evento(proyecto, tipo_evento, entidad, entidad_id, descripcion, antes=None,
    despues=None, usuario=None)` en `apps/core/services.py`, que es la que usarán las acciones
    de negocio (aprobar, publicar, cambiar estado) para escribir eventos con significado, no solo
    el `ACTUALIZACION` genérico.

### 2.5 Permisos reutilizables

12. `apps/core/permissions.py` con las clases de `docs/api-contrato.md` §8:
    `EsAdmin`, `EsPmoOAdmin`, `EsLiderDelProyecto`, `EsDuenoDelRegistro`, `SoloLectura`,
    `EsAdminOSoloLectura`. En esta fase se escriben **vacías de lógica de rol** (devuelven
    `request.user.is_authenticated`) con un `TODO fase-03`, y la fase 03 las completa.
13. `apps/core/mixins.py`: `MixinAlcancePorRol` con un método
    `filtrar_por_rol(self, queryset)` que cada ViewSet llamará desde `get_queryset()`.
    La implementación real llega en la fase 03; aquí se define la interfaz.

### 2.6 Utilidades de dominio

14. `apps/core/periodos.py`: funciones puras, con pruebas unitarias propias, que las fases 08 y
    09 van a usar sin reimplementar:
    - `normalizar_periodo(periodicidad, fecha)` → `(periodo_inicio, periodo_fin)`
      (diaria: el mismo día; semanal: lunes a domingo; mensual: primer y último día del mes).
    - `periodos_entre(periodicidad, desde, hasta)` → lista de periodos.
    - `dias_habiles(desde, hasta)` → entero (sin festivos; se documenta la limitación).
15. `apps/core/calculos.py`: `division_segura(numerador, denominador)` que devuelve `None`
    cuando el denominador es 0 o nulo. **Todo porcentaje de la aplicación pasa por aquí.**

### 2.7 Documentación OpenAPI

16. Configura `SPECTACULAR_SETTINGS`: título "API Seguimiento de Proyectos TI", versión
    `1.0.0`, descripción, `SERVE_INCLUDE_SCHEMA=False`, `COMPONENT_SPLIT_REQUEST=True`.
17. Verifica que las tres rutas de `docs/api-contrato.md` §10 respondan.
18. Añade una prueba que ejecute `python manage.py spectacular --validate --fail-on-warn` para
    que un endpoint mal documentado rompa la suite.

### 2.8 Pruebas

19. `apps/core/tests/`:
    - `test_paginacion.py`: forma de la respuesta, `page_size` respetado, tope de 200.
    - `test_errores.py`: cada código de `docs/api-contrato.md` §9 se produce y tiene el sobre correcto.
    - `test_periodos.py`: los tres tipos de periodicidad, incluidos los bordes (semana que
      cruza de mes, mes de febrero, año nuevo).
    - `test_calculos.py`: `division_segura` con 0 y con `None`.
    - `test_auditoria.py`: al crear y modificar un objeto se escriben las entradas de bitácora
      con el usuario correcto y el diff esperado.

---

## Criterios de aceptación

- [ ] Un error de validación en cualquier endpoint devuelve el sobre `{"error": {...}}` completo.
- [ ] Un error de constraint de Postgres se muestra traducido al español, sin texto crudo del motor.
- [ ] Crear y modificar un registro deja entradas en `EntradaBitacora` con usuario y diff.
- [ ] `normalizar_periodo` pasa las pruebas de borde (cruce de mes, febrero, fin de año).
- [ ] `python manage.py spectacular --validate --fail-on-warn` termina sin advertencias.
- [ ] `pytest` verde y `ruff check backend/` sin hallazgos.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest -q
docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
docker compose -f infra/docker-compose.yml exec backend ruff check .
curl -s -X POST http://localhost:8000/api/v1/salud/ -d '{}' -H "Content-Type: application/json"
```

## Fuera de alcance de esta fase

Lógica de roles (fase 03), endpoints de negocio (fases 05 a 10), frontend.

## Evidencia

<!-- Pega aquí la salida real de los comandos de verificación. -->
