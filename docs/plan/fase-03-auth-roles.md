# Fase 03 — Autenticación JWT, Google OAuth 2.0 y roles

**Rama:** `fase-03-auth-roles` · **Depende de:** fase 02 · **Esfuerzo:** 1–2 sesiones

## Objetivo

Cubrir los objetivos 2 y 3 del usuario: login con JWT propio, login con Google mediante
OAuth 2.0 (Authorization Code + PKCE) y el sistema de roles básico con permisos efectivos
en **dos capas** (permiso de objeto y filtrado de listados).

## Precondiciones

- Fase 02 terminada.
- Lee `docs/api-contrato.md` §2 y §8, y `PLAN.md` §5.
- Credenciales de Google: el usuario debe crear un "OAuth 2.0 Client ID" de tipo
  **Web application** en Google Cloud Console, con `http://localhost:4200/auth/google/callback`
  como URI de redirección autorizada, y poner `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`
  en `.env`. **Si aún no las tiene, implementa todo igual**: los endpoints deben responder
  503 con `codigo: "OAUTH_NO_CONFIGURADO"` y mensaje claro cuando falte la configuración, y
  el botón de Google en la UI se oculta si `GET /auth/google/autorizar/` devuelve 503.

---

## Pasos

### 3.1 JWT propio

1. Configura `SIMPLE_JWT` en `base.py`: `ACCESS_TOKEN_LIFETIME` y `REFRESH_TOKEN_LIFETIME`
   desde `.env`, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`,
   `UPDATE_LAST_LOGIN=True`, `USER_ID_FIELD="id"`, `AUTH_HEADER_TYPES=("Bearer",)`.
   Añade `rest_framework_simplejwt.token_blacklist` a `INSTALLED_APPS` y migra.
2. `apps/accounts/serializers.py`:
   - `UsuarioSerializer` con la forma exacta de `docs/api-contrato.md` §2 (incluye `roles` y
     `permisos_ui`).
   - `LoginSerializer(TokenObtainPairSerializer)` que autentica por `email`, bloquea usuarios
     `is_active=False` y usuarios con `proveedor_auth="GOOGLE"` (mensaje: "Esta cuenta inicia
     sesión con Google"), y añade al token los claims `roles` y `nombre_completo`.
   - `CambiarClaveSerializer` que valida la clave actual y aplica los validadores de Django a
     la nueva; al cambiarla pone `debe_cambiar_clave=False`.
3. `apps/accounts/views.py`: las vistas de `/auth/login/`, `/auth/refresh/`, `/auth/logout/`,
   `/auth/yo/` (GET y PATCH) y `/auth/cambiar-clave/`.
   - `logout` recibe el `refresh` y lo mete en la blacklist; responde 204 incluso si el token
     ya estaba vencido (el cliente no debe quedar bloqueado).
   - `yo` actualiza `ultimo_acceso_en`.
4. Cada login y logout escribe `EntradaBitacora` con `tipo_evento="LOGIN"` usando
   `registrar_evento` de la fase 02 (proyecto en `null`).
5. **Límite de intentos:** `apps/accounts/throttling.py` con un `ScopedRateThrottle`
   `login = "5/min"` por IP + email. Aplícalo a `/auth/login/` y a `/auth/google/callback/`.

### 3.2 Google OAuth 2.0 (Authorization Code + PKCE)

6. `apps/accounts/oauth.py` con el servicio, sin lógica de vista dentro:
   - `construir_url_autorizacion()` → genera `state` (firmado con `DJANGO_SECRET_KEY` y con
     caducidad de 10 minutos) y devuelve la URL de Google con
     `client_id`, `redirect_uri`, `response_type=code`, `scope="openid email profile"`,
     `code_challenge`, `code_challenge_method=S256`, `state`, `access_type=online`,
     `prompt=select_account`.
   - `canjear_codigo(code, code_verifier)` → `POST https://oauth2.googleapis.com/token`,
     devuelve el `id_token`.
   - `verificar_id_token(id_token)` → usa `google.oauth2.id_token.verify_oauth2_token` con el
     `GOOGLE_CLIENT_ID`. **Nunca decodifiques el token a mano.** Valida `iss`, `aud`, `exp` y
     `email_verified=True`.
   - `obtener_o_crear_usuario(info)`:
     - Busca por `google_sub`; si lo encuentra, entra.
     - Si no, busca por `email`: si existe, vincula (`google_sub`) y registra el evento.
     - Si no existe, **crea** el usuario con `proveedor_auth="GOOGLE"`, clave inutilizable,
       `is_active=True` y el rol `CONSULTA` por defecto (el `ADMIN` luego le sube el rol).
     - Si `GOOGLE_DOMINIOS_PERMITIDOS` no está vacío y el dominio del correo no está en la
       lista, rechaza con 403 y mensaje explícito.
7. `/auth/google/autorizar/` devuelve `{url_autorizacion, state}`. El `code_verifier` lo
   genera y guarda el **frontend** (en `sessionStorage`), no el backend.
8. `/auth/google/callback/` recibe `{code, state, code_verifier}`, valida el `state`, canjea,
   verifica, resuelve el usuario y devuelve **tokens propios** con la misma forma que
   `/auth/login/`. A partir de aquí la app solo conoce su propio JWT.
9. Pruebas con el cliente de Google simulado (`unittest.mock`): token válido, token con `aud`
   incorrecto, `email_verified=False`, dominio no permitido, `state` vencido, usuario existente
   que se vincula. **No se hacen llamadas de red en las pruebas.**

### 3.3 Roles

10. `apps/accounts/management/commands/seed_roles.py`: crea los cinco `Group` + `RolMeta`
    de `PLAN.md` §5, asigna los permisos de Django correspondientes a cada grupo y es
    idempotente. Se invoca también desde `seed_demo`.
11. `apps/accounts/permisos_ui.py`: diccionario `PERMISOS_POR_ROL` que mapea cada código de rol
    a su lista de cadenas `permisos_ui` (`"proyectos.crear"`, `"ejecucion.aprobar"`,
    `"seguimientos.publicar"`, `"admin.usuarios"`, …). Función `permisos_de(usuario)` que une
    los permisos de todos sus roles. Es la **única** fuente de esa lista; el frontend no la
    reconstruye.
12. Completa `apps/core/permissions.py` (los `TODO fase-03` de la fase 02):
    - `EsAdmin`, `EsPmoOAdmin`: por código de rol.
    - `EsLiderDelProyecto`: en `has_object_permission`, resuelve el proyecto del objeto con el
      mapa `RUTA_A_PROYECTO` de la fase 02 y compara con `gerente` y `lider_tecnico`.
    - `EsDuenoDelRegistro`: compara `obj.registrado_por` o `obj.recurso.usuario` con el usuario.
    - `SoloLectura`: solo métodos seguros.
13. Completa `MixinAlcancePorRol.filtrar_por_rol`:
    - `ADMIN`, `PMO`, `CONSULTA`: todo.
    - `LIDER`: proyectos donde es `gerente` o `lider_tecnico`, y los objetos de esos proyectos.
    - `RECURSO`: proyectos donde tiene `AsignacionRecurso` activa, y de esos proyectos solo sus
      propias tareas y registros de ejecución.
    - Si el usuario no tiene ningún rol, `queryset.none()` y nunca `all()`.
14. `apps/accounts/views.py`: `UsuarioViewSet` (solo `ADMIN`) con las acciones `activar`,
    `desactivar` y `asignar-roles`; `RolViewSet` de lectura para todos y escritura para `ADMIN`,
    que impide borrar los `es_sistema`.

### 3.4 Pruebas de permisos (lo más importante de la fase)

15. `apps/accounts/tests/test_permisos.py`, con una tabla parametrizada que recorra
    **toda** la matriz de `docs/api-contrato.md` §8: para cada rol y cada recurso, verifica el
    código de respuesta esperado en `list`, `retrieve`, `create`, `update` y `destroy`.
16. Pruebas específicas de fuga de datos:
    - Un `LIDER` que lista `/proyectos/` **no** ve proyectos ajenos (verifica `count`).
    - Un `RECURSO` que lista `/registros-ejecucion/` solo ve los suyos.
    - Un `RECURSO` que pide por id el registro de otro recibe **404**, no 403 (no se revela la
      existencia del recurso).
    - Un usuario sin roles recibe listas vacías, no errores 500.

---

## Criterios de aceptación

- [x] `POST /auth/login/` con los usuarios de `seed_demo` devuelve `access`, `refresh` y `usuario`.
- [x] `GET /auth/yo/` con el token devuelve `roles` y `permisos_ui` correctos para cada rol.
- [x] `POST /auth/refresh/` rota el refresh y el anterior queda invalidado.
- [x] `POST /auth/logout/` deja el refresh inservible (el siguiente `refresh` da 401).
- [x] Seis intentos de login fallidos en un minuto devuelven 429.
- [x] `GET /auth/google/autorizar/` devuelve una URL válida de Google con `code_challenge`,
      o 503 con `OAUTH_NO_CONFIGURADO` si falta la configuración (es el caso de este entorno:
      no hay credenciales reales de Google en `.env`, verificado con `curl`).
- [x] El flujo de Google simulado crea el usuario, lo vincula si ya existía y devuelve JWT propio.
- [x] La matriz de permisos pasa en `test_permisos.py` — **con una salvedad anotada**: los
      recursos de negocio (proyectos, tareas, registros de ejecución, ...) todavía no tienen
      `ViewSet` ni URL (llegan en las fases 05 a 10, fuera de alcance aquí). Lo que esta fase
      construye —`apps/core/permissions.py` y `MixinAlcancePorRol`— se prueba directamente
      contra los modelos reales en vez de inventar ViewSets de relleno; las fases 05+ solo
      conectan estas piezas ya probadas a sus ViewSets.
- [x] Ningún listado filtra de más ni de menos para `LIDER` y `RECURSO` (verificado a nivel de
      queryset con `MixinAlcancePorRol`, por la misma razón anterior).
- [x] `pytest` verde, `ruff` limpio, OpenAPI válido.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend python manage.py seed_roles
docker compose -f infra/docker-compose.yml exec backend pytest apps/accounts -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"lider@demo.local","password":"demo12345"}'
curl -s http://localhost:8000/api/v1/auth/google/autorizar/
```

## Fuera de alcance de esta fase

Pantallas de login (fase 04), recuperación de contraseña por correo, autenticación de dos
factores, otros proveedores OAuth además de Google.

## Evidencia

```
$ docker compose -f infra/docker-compose.yml exec backend python manage.py seed_roles
Roles y permisos sembrados.

$ docker compose -f infra/docker-compose.yml exec backend pytest apps/accounts -q
.................................................                        [100%]
49 passed in 62.41s

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 67%]
..................................                                       [100%]
106 passed in 81.23s

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
No changes detected

$ docker compose -f infra/docker-compose.yml exec backend python manage.py spectacular --validate --fail-on-warn
(exit code 0, sin advertencias)

$ curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"lider@seguimiento.local","password":"Seguimiento2026!"}'
{"refresh":"eyJ...", "access":"eyJ...",
 "usuario":{"id":"24f1427e-...","email":"lider@seguimiento.local","nombres":"Laura",
 "apellidos":"Idárraga", ..., "roles":["LIDER"],
 "permisos_ui":["asignaciones.crear","asignaciones.editar","bitacora.ver","ejecucion.aprobar",
 "ejecucion.crear","ejecucion.editar","ejecucion.ver","expediente.crear","expediente.editar",
 "expediente.ver","fases.crear","fases.editar","gastos.crear","proyectos.editar",
 "proyectos.ver","seguimientos.crear","seguimientos.editar","seguimientos.publicar",
 "seguimientos.ver","tablero.ver","tareas.crear","tareas.editar","tareas.ver"]}}

$ curl -s -i "http://localhost:8000/api/v1/auth/google/autorizar/?code_challenge=abc"
HTTP/1.1 503 Service Unavailable
{"error":{"codigo":"OAUTH_NO_CONFIGURADO",
 "mensaje":"El inicio de sesión con Google no está configurado en este entorno.",
 "detalles":null,"traza_id":"d996ce9183bb"}}
(correcto: este entorno no tiene GOOGLE_CLIENT_ID/SECRET reales en .env)

$ ACCESS=$(curl ... admin@seguimiento.local ...)
$ curl -s http://localhost:8000/api/v1/auth/yo/ -H "Authorization: Bearer $ACCESS"
{"id":"436222a0-...","email":"admin@seguimiento.local","nombres":"Ana","apellidos":"Dirección",
 ...,"roles":["ADMIN"],
 "permisos_ui":["admin.roles","admin.usuarios","bitacora.ver","catalogos.borrar", ... 31 en total],
 "proyectos_liderados":[]}
```

**Dos bugs reales encontrados y corregidos durante la fase** (con prueba de regresión cada
uno, ya incluida en el conteo de 106 pruebas):

1. `EsDuenoDelRegistro.has_object_permission` se quedaba con la primera señal de pertenencia
   que existiera como atributo (`registrado_por_id`), aunque fuera `None`, en vez de probar
   las tres (`registrado_por`, `recurso.usuario`, `responsable.usuario`) y aceptar si
   cualquiera coincidía. Además comparaba `responsable_id` (el id de un `Recurso`)
   directamente contra el id de un `Usuario` — nunca podía coincidir. Corregido para resolver
   `responsable.usuario_id` y para no descartar las otras señales cuando la primera es nula.
2. `ScopedRateThrottle.allow_request()` lee el *scope* de `view.throttle_scope` (atributo de
   la vista), no de un atributo de la clase del throttle. El `scope = "login"` que había
   puesto en `LoginRateThrottle` nunca se usaba, así que el límite de intentos no limitaba
   nada. Corregido añadiendo `throttle_scope = "login"` a `LoginView` y `GoogleCallbackView`.

**Decisión de alcance anotada** (no es un bug, es una limitación real del momento del plan):
los recursos de negocio del §8 de `docs/api-contrato.md` (proyectos, tareas, registros de
ejecución, gastos, seguimientos, documentos) no tienen `ViewSet` todavía — llegan en las
fases 05 a 10. `test_permisos.py` prueba las clases de `apps/core/permissions.py` y
`MixinAlcancePorRol` directamente contra los modelos reales (incluida la ruta indirecta
`DependenciaTarea→tarea_origen→proyecto`, y la comprobación de que un `RECURSO` pidiendo por
id el registro de otro obtiene `DoesNotExist` → 404, nunca una denegación de permiso → 403),
en vez de inventar ViewSets de relleno para "completar" la matriz antes de tiempo.
