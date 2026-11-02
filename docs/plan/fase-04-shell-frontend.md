# Fase 04 — Shell del frontend y biblioteca de UI

**Rama:** `fase-04-shell-frontend` · **Depende de:** fase 03 · **Esfuerzo:** 2 sesiones

## Objetivo

Dejar el panel administrativo navegable: login (clave y Google), layout con menú lateral,
sesión persistente, manejo global de errores y los **18 componentes propios** de
`shared/ui/` que las fases 05 a 10 van a reutilizar sin crear variantes.

Esta es la fase que más deuda evita: si los componentes base quedan completos, las pantallas
siguientes son composición.

## Precondiciones

- Fase 03 terminada y el backend corriendo con `seed_demo`.
- Lee `PLAN.md` §4 (convenciones de frontend) y `docs/api-contrato.md` §2 y §9.

---

## Pasos

### 4.1 Núcleo (`src/app/core/`)

1. `core/config/app.config.ts`: `provideHttpClient(withInterceptors([...]))`,
   `provideRouter(rutas, withComponentInputBinding())`, `provideZonelessChangeDetection()`
   si la versión instalada lo soporta (si no, omítelo).
2. `core/models/`: una interfaz por entidad, con nombres de campo **idénticos** al JSON del
   backend. Deriva los tipos de `docs/modelo-datos.md`. Los enumerados se declaran como
   uniones de literales (`export type EstadoProyecto = 'BORRADOR' | 'PLANEACION' | ...`) y
   además un objeto `ETIQUETAS_ESTADO_PROYECTO` con la etiqueta en español para la UI.
   Tipos genéricos: `RespuestaPaginada<T>` y `ErrorApi` según `docs/api-contrato.md` §1 y §9.
3. `core/auth/auth.service.ts`:
   - Estado con signals: `usuario = signal<Usuario | null>(null)`,
     `autenticado = computed(...)`, `cargando = signal(false)`.
   - `login(email, clave)`, `loginGoogle()`, `completarLoginGoogle(code, state)`,
     `logout()`, `refrescar()`, `cargarUsuario()`.
   - Tokens en `localStorage` bajo las claves `sp_access` y `sp_refresh`.
     Al arrancar la app, si hay refresh válido, se restaura la sesión antes de pintar las rutas
     protegidas (usa un `APP_INITIALIZER` o `provideAppInitializer`).
   - `tienePermiso(codigo: string)` y `tieneRol(codigo: string)`, basados en lo que devuelve
     `/auth/yo/`. **Nunca se reconstruyen permisos en el cliente.**
4. `core/auth/google.ts`: generación del `code_verifier` (43–128 caracteres aleatorios) y del
   `code_challenge` con SHA-256 y base64url usando `crypto.subtle`. El `code_verifier` se
   guarda en `sessionStorage` y se borra al completar el intercambio.
5. `core/http/`:
   - `auth.interceptor.ts`: añade `Authorization: Bearer`; ante un 401 intenta **un solo**
     refresh y reencola las peticiones en vuelo; si el refresh falla, limpia sesión y redirige
     a `/auth/login` con `returnUrl`.
   - `error.interceptor.ts`: traduce la respuesta a `ErrorApi`, muestra el `mensaje` en un
     toast (salvo en 401, que ya maneja el anterior) y **repropaga** el error para que el
     formulario pueda pintar `detalles` campo por campo.
   - `cargando.interceptor.ts`: cuenta peticiones activas y alimenta una barra de progreso
     superior.
6. `core/guards/`: `autenticadoGuard`, `rolGuard(codigos: string[])`,
   `permisoGuard(codigo: string)` y `cambioClaveGuard` (si `debe_cambiar_clave`, fuerza la
   ruta de cambio de contraseña). Todos funcionales (`CanActivateFn`).
7. `core/api/api.service.ts`: envoltura genérica tipada sobre `HttpClient`
   (`listar<T>(ruta, params)`, `obtener<T>`, `crear<T>`, `actualizar<T>`, `eliminar`,
   `accion<T>(ruta, id, nombre, cuerpo)`). Los servicios de cada feature la extienden; **ningún
   componente la usa directamente**.
8. `core/ui/toast.service.ts` y `confirmacion.service.ts`: servicios con signals que alimentan
   los componentes correspondientes montados una sola vez en el shell.

### 4.2 Biblioteca de UI (`src/app/shared/ui/`) — los 18 componentes

Todos `standalone`, `OnPush`, con `input()` / `output()` de la API de signals, accesibles
(roles ARIA, foco visible, navegación por teclado) y **solo** con los tokens de
`tailwind.config.js`.

| # | Componente | Selector | Requisitos clave |
|---|------------|----------|------------------|
| 1 | Botón | `app-boton` | variantes `primario \| secundario \| peligro \| fantasma`, tamaños `sm \| md`, estado `cargando` con spinner, `disabled` |
| 2 | Input de texto | `app-input` | etiqueta, ayuda, mensaje de error, prefijo/sufijo, `ControlValueAccessor` |
| 3 | Área de texto | `app-textarea` | contador de caracteres opcional |
| 4 | Select | `app-select` | opciones `{valor, etiqueta}`, búsqueda si hay más de 10, limpiable |
| 5 | Selector de fecha | `app-datepicker` | formato `dd/MM/yyyy`, calendario propio, mín./máx., teclado |
| 6 | Input numérico | `app-numero` | separador de miles es-CO, decimales configurables, modo moneda y modo horas |
| 7 | Casilla / interruptor | `app-switch` | |
| 8 | Tabla | `app-tabla` | columnas declarativas, orden por columna, paginación conectada a `RespuestaPaginada`, estado de carga con esqueleto, estado vacío, selección opcional, plantillas de celda con `ng-template` |
| 9 | Modal | `app-modal` | tamaños, cierre con Esc, trampa de foco, scroll bloqueado |
| 10 | Panel lateral | `app-drawer` | mismo contrato que el modal, para formularios largos |
| 11 | Pestañas | `app-tabs` | accesibles con flechas |
| 12 | Etiqueta de estado | `app-badge` | mapea cada enumerado de estado a su color de token |
| 13 | Tarjeta | `app-card` | título, acciones en la cabecera, pie opcional |
| 14 | Toast | `app-toast` | pila, autocierre, tipos éxito/alerta/error/info |
| 15 | Diálogo de confirmación | `app-confirmacion` | promesa/signal, texto configurable, variante peligro |
| 16 | Estado vacío | `app-estado-vacio` | icono, mensaje, acción sugerida |
| 17 | Barra de progreso | `app-progreso` | valor 0–100, variante por umbral, etiqueta con el porcentaje |
| 18 | Semáforo | `app-semaforo` | `VERDE \| AMARILLO \| ROJO`, con texto accesible además del color |

Reglas transversales:
- **El color nunca es el único portador de significado**: el semáforo y los badges llevan
  texto o icono; el progreso lleva su porcentaje escrito.
- Contraste mínimo 4.5:1 para texto sobre fondo coloreado.
- Ninguna dependencia externa de UI. `chart.js` entra solo en la fase 10.

9. `shared/pipes/`: `moneda` (es-CO, muestra `—` si es `null`), `horas` (`1.234,50 h`),
   `porcentaje` (un decimal, `—` si es `null`), `fechaCorta`, `etiquetaEnum`.
10. `shared/ui/catalogo/`: ruta interna `/dev/catalogo` (solo visible con `DEBUG`) que muestra
    los 18 componentes en todos sus estados. Es la prueba visual de la fase.

### 4.3 Shell (`src/app/layout/`)

11. `layout/shell.component.ts`: barra superior (logo, buscador global desactivado por ahora,
    menú de usuario con nombre, rol, cambiar contraseña y salir), menú lateral colapsable con
    los grupos del panel y migas de pan.
12. Menú lateral, con sus permisos de visibilidad:

    | Grupo | Rutas | Visible con |
    |-------|-------|-------------|
    | Tablero | `/tablero` | cualquiera autenticado |
    | Proyectos | `/proyectos` | cualquiera autenticado |
    | Tareas | `/tareas` | cualquiera autenticado |
    | Ejecución | `/ejecucion/registros`, `/ejecucion/aprobaciones` | `ejecucion.registrar` / `ejecucion.aprobar` |
    | Seguimientos | `/seguimientos` | cualquiera autenticado |
    | Recursos | `/recursos`, `/recursos/asignaciones` | `recursos.ver` |
    | Administración | `/admin/usuarios`, `/admin/roles`, `/admin/catalogos` | `admin.usuarios` |

    Los ítems sin permiso **no se renderizan**; además las rutas están protegidas por guard.
13. Rutas base en `app.routes.ts`: `/auth/*` sin shell; todo lo demás dentro del shell con
    `canActivate: [autenticadoGuard, cambioClaveGuard]` y `loadChildren` por feature.
    Rutas de las fases 05 a 10 se declaran ahora como marcadores que cargan un componente
    "En construcción", para que el menú funcione completo desde esta fase.
14. Página 404 y página 403 propias.

### 4.4 Autenticación en la UI (`features/auth/`)

15. `login.component`: formulario tipado (email, clave), mensajes de error desde
    `error.detalles`, enlace "¿Olvidó su contraseña?" deshabilitado con tooltip
    ("Solicítelo al administrador" — la recuperación por correo está fuera del alcance v1),
    y botón "Continuar con Google" que se **oculta** si `/auth/google/autorizar/` devuelve 503.
16. `google-callback.component`: lee `code` y `state` de la URL, recupera el `code_verifier`
    de `sessionStorage`, llama a `/auth/google/callback/`, guarda tokens y navega al
    `returnUrl` o a `/tablero`. Si falla, vuelve a `/auth/login` con el mensaje de error.
17. `cambiar-clave.component`: obligatorio cuando `debe_cambiar_clave` es `true`.
18. `perfil.component`: edita `nombres`, `apellidos`, `cargo`, `telefono` vía `PATCH /auth/yo/`.

### 4.5 Pruebas

19. Pruebas unitarias de: `auth.service` (login, refresh único ante 401 concurrente, logout),
    `auth.interceptor` (no reintenta en bucle), los guards y el componente `app-tabla`
    (orden, paginación, estado vacío).
20. Elimina el componente de prueba de `/salud/` que creó la fase 00.

---

## Criterios de aceptación

- [x] Login con `lider@demo.local` entra al panel y el menú muestra solo lo permitido a `LIDER`.
      Verificado por lógica (sidebar filtra `ITEMS_MENU` por `permisos_ui`, probado
      transitivamente vía `permisoGuard`/`rolGuard`) y por `curl` contra el backend real (ver
      Evidencia); **no** se pudo abrir un navegador real en este entorno para verlo pintado.
- [x] Al recargar la página la sesión se mantiene (se restaura desde el refresh).
      `AuthService.restaurarSesion()` corre vía `provideAppInitializer`; su lógica
      (refrescar → cargarUsuario → limpiar si falla) tiene prueba unitaria directa.
- [x] Con el access token vencido, la siguiente petición lo refresca sola y no expulsa al usuario.
      Prueba de `auth.interceptor.spec.ts`: dos 401 concurrentes disparan un único refresh y
      ambas peticiones se reintentan con el token nuevo.
- [x] Un refresh inválido limpia la sesión y redirige a `/auth/login?returnUrl=...`.
      Prueba: refresh que falla → `limpiarSesion()` (tokens borrados) y se llama a
      `router.navigate(['/auth/login'], {queryParams:{returnUrl}})`.
- [x] Entrar a `/admin/usuarios` como `RECURSO` muestra la página 403, no un error de consola.
      `permisoGuard('admin.usuarios')` probado: sin el permiso devuelve el `UrlTree` de `/403`.
- [x] `/dev/catalogo` muestra los 18 componentes y todos operan con teclado. Construida; cada
      componente interactivo tiene su propio manejo de teclado (Tab/Esc/flechas/Enter) descrito
      en su código. **No** se pudo operar con un navegador real en este entorno para confirmarlo
      a mano.
- [x] Un error 400 del backend pinta el mensaje en el toast **y** el detalle bajo cada campo.
      `errorInterceptor` muestra el toast para todo error que no sea 401; `login`/`cambiar-clave`
      leen `error.detalles` y lo pasan a `app-input` como `error` por campo.
- [x] `npm run build` y `npm run lint` limpios; `npm test` verde (25 pruebas).
- [x] Ningún archivo `.html` tiene un color literal; todo sale de los tokens de Tailwind.
- [x] No hay ni un `any` en `src/app/`.

## Comandos de verificación

```bash
cd frontend
npm run lint
npm run build
npm test -- --watch=false
grep -rn "bg-\[#\|text-\[#" src/app  # debe no devolver nada
grep -rn ": any\|<any>" src/app      # debe no devolver nada
```

## Fuera de alcance de esta fase

Pantallas de negocio con datos reales (fases 05 a 10), gráficos, carga de archivos.
Las rutas de negocio quedan como marcadores "En construcción".

## Evidencia

Nota de entorno: no hay navegador disponible en esta sesión (igual que en fases anteriores),
así que el login/el catálogo de componentes/la navegación por teclado no se pudieron
verificar a ojo en un navegador real. Se verificó todo lo que sí es verificable sin uno:
compilación, lint, pruebas unitarias, greps de las reglas de estilo, y el backend real por
`curl` (ya cubierto end-to-end en la fase 03).

```
$ cd frontend && npm run lint
All files pass linting.

$ npm run build
Initial chunk files | Names  |  Raw size | Estimated transfer size
main-DLCPTZDG.js    | main   | 384.94 kB |                97.23 kB
styles-H2YKKQQC.css | styles |  18.03 kB |                 3.52 kB
                    | Initial total | 402.97 kB |          100.76 kB
Application bundle generation complete. [14.689 seconds]

$ npm test -- --watch=false
 ✓ src/app/app.spec.ts (1 test)
 ✓ src/app/core/auth/auth.service.spec.ts (5 tests)
 ✓ src/app/core/guards/guards.spec.ts (9 tests)
 ✓ src/app/core/http/auth.interceptor.spec.ts (4 tests)
 ✓ src/app/shared/ui/tabla/tabla.spec.ts (6 tests)
 Test Files  5 passed (5)
      Tests  25 passed (25)

$ grep -rn "bg-\[#\|text-\[#" src/app   # vacío
$ grep -rn ": any\|<any>" src/app      # vacío
```

**Bugs reales encontrados y corregidos durante la fase:**

1. `<app-boton class="w-full">` no funcionaba: una clase puesta en el elemento host de un
   componente Angular no llega al `<button>` interno salvo que el propio componente la
   reenvíe. Se corrigió agregando un input `completo` a `Boton` en vez de depender de una
   clase externa.
2. Las plantillas de `app-modal`/`app-drawer` usaban `(keydown.tab)="alTeclaTab($event)"`:
   Angular tipa los modificadores de tecla no estándar (`.tab`, a diferencia de `.escape`)
   como `Event` genérico, no `KeyboardEvent`, y el build fallaba. Se cambió a `(keydown)`
   con el filtro `evento.key === 'Tab'` dentro del método.
3. `select.html` tenía un error de parseo de plantilla por una expresión inline con `as` y
   paréntesis anidados; se extrajo a un método `alBuscar()`.
4. `app-textarea` usaba `[maxlength]` (nombre de atributo HTML) en vez de la propiedad DOM
   (`maxLength`); con un valor `number | null` ninguna de las dos ataba bien, así que se usó
   `[attr.maxlength]`, que además maneja `null` quitando el atributo correctamente.
5. Varias reglas reales de accesibilidad de `@angular-eslint/template`: el backdrop de
   modal/drawer (clic para cerrar) necesitaba `aria-hidden="true"` para no contarse como
   control interactivo sin equivalente de teclado (Esc y el botón "Cerrar" ya lo cubren); el
   combobox de `app-select` le faltaba `aria-controls`, su "label" no podía ser un `<label>`
   real (no envuelve un control nativo) y sus opciones necesitaban ser alcanzables sin
   depender solo del `click`.
6. Rechazo de promesa sin manejar en `auth.interceptor.ts`: `router.navigate(...)` tras un
   refresh fallido puede rechazar (p. ej. si otro guard cancela la navegación) y nada lo
   capturaba. Se le agregó `.catch(() => undefined)`.

Estos se encontraron por el propio `ng build`/`ng lint`/`npm test`, no se buscaron a propósito;
quedan documentados porque cada uno habría sido un defecto real en producción.
