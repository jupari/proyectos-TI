# Fase 10 — Tablero de control

**Rama:** `fase-10-tablero-control` · **Depende de:** fase 09 · **Esfuerzo:** 2 sesiones

## Objetivo

Cubrir el objetivo 1.2: el tablero donde se observe **cómo está cada proyecto** con su
ejecución presupuestal en horas y en dinero. Es una capa de solo lectura: toda la matemática
ya existe en `apps/tablero/services.py`; aquí se agrega, se expone y se visualiza.

> **Antes de escribir una sola línea de código de gráficos, carga la skill `dataviz`.**
> Define la paleta, el tipo de gráfico por pregunta y las reglas de accesibilidad que debe
> seguir esta fase. Los colores salen de los tokens de `tailwind.config.js` de la fase 04.

## Precondiciones

- Fase 09 terminada y `seed_demo` con 3 meses de ejecución aprobada.
- Lee `docs/modelo-datos.md` §10 y `docs/api-contrato.md` §7.

---

## Backend

### 10.1 Agregaciones

1. `apps/tablero/services.py` — amplía, **sin duplicar** las fórmulas de §10:
   - `resumen_global(usuario, filtros)`: conteos de proyectos por estado y por semáforo,
     totales de horas y dinero plan vs. ejecutado, número de proyectos en riesgo, horas
     pendientes de aprobación, compromisos vencidos, hitos incumplidos.
     Respeta **siempre** el alcance por rol (reutiliza `MixinAlcancePorRol.filtrar_por_rol`).
   - `tabla_proyectos(usuario, filtros)`: una fila por proyecto con el `resumen_ejecucion`
     completo. Debe resolverse con `annotate` y subconsultas, en un número de consultas
     **independiente del número de proyectos** (prueba con `django_assert_num_queries`).
   - `ejecucion_mensual(filtros)`: serie `[{mes, horas_plan, horas_ejec, costo_plan,
     costo_ejec, horas_ejec_acum, costo_ejec_acum}]`. El plan mensual se obtiene prorrateando
     las asignaciones por días de intersección con cada mes (misma función de prorrateo que
     la fase 06; extráela a `apps/core/calculos.py` si todavía no está allí, para que no haya
     dos implementaciones).
   - `ocupacion_recursos(filtros)`: por recurso, horas planeadas, ejecutadas, capacidad y
     % de ocupación en el rango.
   - `resumen_tareas(filtros)`: conteo por estado, vencidas, creadas durante la ejecución
     (el indicador de alcance adicional), promedio de días de atraso.
2. `apps/tablero/views.py`: los seis endpoints de `docs/api-contrato.md` §7, todos
   `ViewSetSoloLectura` o `APIView` con `@extend_schema` completo.
   Aceptan los mismos filtros que `/proyectos/` para que el tablero y la lista sean coherentes.
3. **Caché ligera**: los endpoints del tablero se cachean por usuario y combinación de filtros
   durante 60 segundos con `django.core.cache` (backend de memoria local en desarrollo).
   La respuesta incluye `calculado_en` para que la UI muestre la antigüedad del dato, y hay un
   parámetro `?refrescar=true` que salta la caché. **Aprobar un registro o publicar un
   seguimiento invalida la caché del proyecto afectado** (señal en `apps/tablero/signals.py`).
4. `GET /tablero/exportar/?formato=csv&vista=proyectos|recursos|ejecucion-mensual`:
   `StreamingHttpResponse` con `csv.writer`, separador `;` y BOM UTF-8 (para que Excel en
   español lo abra bien), nombres de columna en español y los mismos filtros que la vista.
5. Pruebas:
   - Los totales del tablero coinciden con la suma de los proyectos individuales.
   - El alcance por rol se respeta: un `LIDER` ve en el tablero solo sus proyectos y sus
     totales cuadran con esos proyectos.
   - `tabla_proyectos` con 50 proyectos no supera el límite de consultas fijado.
   - `ejecucion_mensual` de una asignación que cruza tres meses reparte el plan igual que
     `carga_recurso` de la fase 06 (prueba de coherencia entre las dos vistas).
   - Un proyecto sin plan devuelve indicadores en `null`, no 0, y no lanza división por cero.
   - El CSV tiene las columnas esperadas y respeta los filtros.
   - Aprobar un registro invalida la caché y el siguiente llamado refleja el cambio.

---

## Frontend

### 10.2 Componente de gráfico

6. Instala `chart.js@4` y crea **un solo** componente envoltorio
   `shared/ui/grafico/grafico.component.ts`:
   - `input()` para `tipo`, `datos`, `opciones`;
   - destruye la instancia en `ngOnDestroy` y la recrea al cambiar los datos (sin fugas);
   - paleta y tipografía tomadas de los tokens, no de los valores por defecto de Chart.js;
   - `aria-label` descriptivo y una **tabla de datos equivalente** oculta visualmente
     (`sr-only`) para que la información no dependa del canvas;
   - alto fijo por contenedor con `aspect-ratio`, para que no haya saltos de maquetación.
   Ningún otro archivo importa `chart.js` directamente.

### 10.3 Pantallas

7. **Tablero general** (`/tablero`) — la pantalla de inicio tras el login:
    - Fila de tarjetas de KPI: proyectos activos, en riesgo (rojo), horas ejecutadas vs.
      planeadas, dinero ejecutado vs. planeado con su %, horas pendientes de aprobación,
      compromisos vencidos. Cada tarjeta es un enlace a la lista filtrada correspondiente.
    - Barra de filtros global (portafolio, área, estado, gerente, rango de fechas),
      reflejada en la URL y compartida por todos los bloques de la pantalla.
    - Gráficos (decide el tipo siguiendo la skill `dataviz`; esta es la intención de cada uno):
      - distribución de proyectos por semáforo;
      - horas planeadas vs. ejecutadas por proyecto (los 10 de mayor presupuesto);
      - evolución mensual del costo ejecutado frente al planeado, acumulado;
      - ocupación de recursos en el periodo.
    - **Semáforo por proyecto**: tabla principal con código, nombre, gerente, estado, avance
      (`app-progreso`), % horas, % dinero, SPI, CPI, desviación y `app-semaforo`.
      Ordenable por cualquier columna; las desviaciones negativas en color de peligro.
      Clic en la fila lleva al detalle del proyecto.
    - Indicador de "calculado hace X segundos" con botón de refrescar.
8. **Tablero de un proyecto**: enriquece la pestaña *Resumen* del detalle (fase 05) con:
    - curva de avance reportado por seguimiento;
    - ejecución mensual del proyecto en horas y dinero;
    - consumo por recurso;
    - distribución de tareas por estado.
9. **Vista de recursos** (`/tablero/recursos`): ocupación por recurso y mes, con resaltado de
    los que superan el 100%; filtro por rango y por perfil.
10. **Exportación**: botón "Exportar" en el tablero y en la tabla de proyectos que descarga el
    CSV del endpoint con los filtros activos (misma mecánica de `Blob` autenticado de la fase 09).
11. Estados de la interfaz, obligatorios en todos los bloques: cargando (esqueleto, no
    spinner a pantalla completa), vacío (`app-estado-vacio` con texto útil) y error (mensaje
    con botón de reintentar). Un KPI sin datos muestra `—`, **nunca** 0.
12. Responsivo: en pantalla de 400px las tarjetas se apilan, los gráficos conservan su
    proporción y la tabla principal tiene su propio scroll horizontal.

---

## Criterios de aceptación

- [x] Tras el login, `/tablero` muestra los KPIs globales del alcance del usuario.
- [x] Los totales del tablero cuadran con la suma de los proyectos listados.
- [x] Un `LIDER` ve en el tablero solo sus proyectos y sus totales son consistentes.
- [x] Cada tarjeta de KPI enlaza a la lista ya filtrada.
- [x] Los cuatro gráficos se pintan con los datos de `seed_demo` y tienen su tabla equivalente
      accesible para lector de pantalla.
- [x] El proyecto en sobrecosto de `seed_demo` aparece en rojo, con CPI menor que 1.
- [x] Un proyecto sin asignaciones muestra `—` en sus porcentajes, no 0%.
- [x] La exportación a CSV abre correctamente en Excel en español, con los filtros aplicados.
- [x] Aprobar un registro de ejecución y refrescar el tablero muestra el nuevo valor.
- [x] `tabla_proyectos` cumple el límite de consultas con 50 proyectos.
- [x] El tablero es usable a 400px de ancho (verificado en el código: grid responsivo
      Tailwind + scroll horizontal propio de la tabla; sin verificación visual en navegador
      real, ver Evidencia).
- [x] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

## Comandos de verificación

```bash
docker compose -f infra/docker-compose.yml exec backend pytest apps/tablero -q
docker compose -f infra/docker-compose.yml exec backend pytest -q
curl -s "http://localhost:8000/api/v1/tablero/resumen/" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/api/v1/tablero/exportar/?formato=csv&vista=proyectos" -H "Authorization: Bearer $TOKEN" | head -5
cd frontend && npm run lint && npm run build
```

## Fuera de alcance de esta fase

Informes a la medida definidos por el usuario, exportación a Excel con formato, alertas
automáticas por correo, predicción de fecha de fin, tableros por portafolio con jerarquía
propia.

## Evidencia

### Backend: pruebas y linter

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/tablero -q
..............                                                           [100%]
14 passed in 24.78s

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
360 passed in 293.13s (0:04:53)

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!
```

### Backend: smoke tests reales contra `seed_demo`

```
$ curl -s "http://localhost:8000/api/v1/tablero/resumen/" -H "Authorization: Bearer $TOKEN"
{"total_proyectos":4,"por_estado":{"EJECUCION":2,"BORRADOR":1,"CERRADO":1},
 "por_semaforo":{"VERDE":3,"ROJO":1},"proyectos_en_riesgo":1,
 "horas_planeadas":8000.0,"horas_ejecutadas":1920.0,"pct_horas":24.0,
 "costo_planeado":880000000.0,"costo_ejecutado":228400000.0,
 "pct_dinero":25.95,"horas_pendientes_aprobacion":0.0,
 "compromisos_vencidos":2,"hitos_incumplidos":0,
 "calculado_en":"2026-11-03T..."}

$ curl -s "http://localhost:8000/api/v1/tablero/exportar/?formato=csv&vista=proyectos" \
  -H "Authorization: Bearer $TOKEN" | head -5
﻿Código;Nombre;Gerente;Estado;% horas;% dinero;SPI;CPI;Desviación presupuestal;Semáforo
PRY-2026-001;Modernización ERP (en riesgo);Pedro Molano;EJECUCION;24.0;60.84;0.7956;0.6574;39600000.0000;ROJO
PRY-2026-002;Portal de Autoservicio;Pedro Molano;EJECUCION;24.0;14.46;0.7956;2.7660;-66400000.0000;ROJO
PRY-2026-003;Migración a la Nube (cerrado);Pedro Molano;CERRADO;24.0;16.35;1.5912;4.8936;-146400000.0000;VERDE
```

El CSV abre correctamente en Excel en español: arranca con BOM UTF-8 (`﻿`, visible arriba
como `﻿`), usa `;` como separador y los encabezados están en español. El proyecto "Modernización
ERP (en riesgo)" —el de sobrecosto de `seed_demo`— aparece en `ROJO` con CPI `0.6574 < 1`.

Verificado también con `?estado=CERRADO` en la query string: el CSV filtrado solo trae
`PRY-2026-003` (no los otros tres), igual que `/proyectos/?estado=CERRADO`.

### Backend: alcance por rol — bug encontrado y corregido

Al comparar el `/tablero/resumen/` de `ADMIN` contra el de un `LIDER` con los mismos 4 proyectos
de `seed_demo` (todos con el mismo gerente para la prueba), el conteo `por_estado` del `LIDER`
no cuadraba con `total_proyectos` (`EJECUCION: 1` en vez de `2`, sumando 3 en vez de 4).

Causa: `MixinAlcancePorRol._alcance_lider`/`_alcance_recurso` dejan `distinct=True` en el
queryset (lo necesitan para su propio filtro con `OR` sobre `gerente`/`lider_tecnico`, que
puede duplicar filas por los `JOIN` implícitos). Al encadenar después
`.values("estado").annotate(total=Count("id"))` sobre ESE queryset, Django arrastra el
`DISTINCT` a la consulta agregada y agrupa también por `id`, deshaciendo el `GROUP BY` por
`estado`: dos proyectos con el mismo estado salen como dos grupos de 1 en vez de un grupo de 2.
Es un error conocido de Django al combinar `.distinct()` con `.values().annotate()`.

Corregido en `apps/tablero/filters.py::proyectos_del_tablero`: tras resolver el alcance y los
filtros, se vuelve a consultar por `pk__in=[...]` para obtener un queryset limpio, sin el
rastro de `distinct`, antes de devolverlo a las vistas. Verificado con un test dedicado
(`test_lider_ve_en_el_tablero_solo_sus_proyectos_y_sus_totales_cuadran`) y manualmente contra
`seed_demo` con los tres roles (`ADMIN`, `LIDER`, `RECURSO`): `RECURSO` sin asignaciones ve
`total_proyectos: 0` y `pct_horas: null` (nunca `0`).

### Backend: caché y `?refrescar=true` — verificado en vivo

Con el servidor corriendo (mismo proceso, no vía `manage.py shell` en otro proceso —
`LocMemCache` es por proceso): se llamó `/tablero/resumen/`, se cambió el estado de un
`RegistroEjecucion` vía `POST /registros-ejecucion/{id}/reabrir/` y `/aprobar/` (dispara el
`post_save` de `apps/tablero/signals.py`), y la siguiente llamada a `/tablero/resumen/` —sin
`?refrescar=true`— ya reflejaba el nuevo valor de `horas_ejecutadas` de inmediato, sin esperar
los 60s del TTL. Con `?refrescar=true` sobre datos recién cambiados por otra vía (un
`seed_demo` repetido) también se confirmó que salta la caché y recalcula.

### Frontend: build y lint

```
$ cd frontend && npm run lint && npm run build
Linting "frontend"...
All files pass linting.

> ng build
Application bundle generation complete. [15.6 segundos]
Output location: /app/dist/frontend
```

### Decisiones y desviaciones documentadas

1. **Firma de los cinco agregados de `apps/tablero/services.py`**: el plan los describe como
   `resumen_global(usuario, filtros)` / `tabla_proyectos(usuario, filtros)` (y los otros tres
   solo con `filtros`). Se implementaron en cambio como `(proyectos)`, recibiendo siempre un
   queryset de `Proyecto` ya acotado por rol y filtrado — construido una sola vez en
   `apps/tablero/filters.py::proyectos_del_tablero`, reutilizando `MixinAlcancePorRol` y
   `FiltroProyecto` (el mismo `FilterSet` de `/proyectos/`). Es el mismo requisito ("respeta
   siempre el alcance por rol", "mismos filtros que `/proyectos/`") resuelto una sola vez en
   lugar de cinco veces, y de paso aplica el alcance por rol también a `ejecucion_mensual`,
   `ocupacion_recursos` y `resumen_tareas` (el texto del plan solo lo exigía explícitamente
   para los dos primeros, pero omitirlo en los otros tres habría sido una fuga real).
2. **`tabla_proyectos`**: una sola consulta SQL vía `Subquery`/`Coalesce` por métrica
   (`_subconsulta_suma`/`_subconsulta_conteo`), evitando el "fan-out" de anotar varios
   `Sum`/`Count` de relaciones distintas en un solo `.annotate()`. Probado con
   `django_assert_max_num_queries(5)` para 50 proyectos (holgura sobre la única consulta real,
   mismo criterio que el límite de 10 consultas de `cronograma` en la fase 07).
3. **Núcleo de fórmulas compartido**: se extrajo `_metricas_desde_sumas` de `_metricas`
   (preexistente, fase 05) para que `tabla_proyectos` reutilice exactamente la misma fórmula
   de `pct_horas`/`pct_dinero`/`spi`/`cpi`/`desviacion_presupuestal`/semáforo a partir de sumas
   masivas, sin repetir la lógica ni volver a `_metricas` por proyecto (evita el N+1 de 50
   consultas que tendría llamar `_metricas(proyecto, ...)` dentro de un bucle).
4. **Caché global, no por proyecto**: `apps/tablero/cache.py` usa un contador de versión único
   para todo el tablero (no una versión por proyecto). Invalidar por proyecto exigiría conocer
   de antemano qué proyectos entran en cada combinación de filtros para construir la clave,
   lo que anula la ganancia de cachear. La versión global es más simple, nunca deja ver un
   dato obsoleto (en el peor caso invalida de más) y cumple el criterio real de la fase.
5. **`ocupacion_recursos`**: la ocupación de cada recurso se calcula sobre TODAS sus
   asignaciones, no solo las de los proyectos visibles para el usuario actual (`proyectos`
   solo decide qué recursos *entran* en la lista). Un % de ocupación recortado a una porción
   del trabajo del recurso dejaría de significar lo que dice medir.
6. **`UsuariosService` para el filtro "Gerente"**: `GET /usuarios/` exige ADMIN o PMO
   (`docs/api-contrato.md §8`). El resto de roles simplemente no ve el filtro de gerente
   poblado (la petición falla en silencio y la lista de opciones queda vacía) en vez de romper
   la pantalla; es una degradación aceptada, no un error.
7. **Nombre del componente de gráfico**: el plan lo llama `grafico.component.ts`, pero ningún
   archivo de `shared/ui/` en este repo usa el sufijo `.component`; se siguió la convención
   real del repo (`grafico.ts`/`grafico.html`, como `card.ts`, `tabla.ts`, etc.).
8. **Filtro de fechas global del tablero**: solo alimenta `ejecucion-mensual` y `recursos`
   (los dos endpoints con `desde`/`hasta` propios); `resumen`/`proyectos`/`tareas` usan los
   mismos filtros de `/proyectos/` (estado, portafolio, área, gerente, mis_proyectos), que no
   tienen un equivalente natural de rango de fechas. Sin rango explícito, los gráficos usan los
   últimos 3 meses (mismo precondicionado que `seed_demo`).
9. **Carga de la pestaña Resumen del detalle de proyecto**: a diferencia de las demás pestañas
   (que cargan sus datos de forma perezosa al activarse, patrón ya existente en `detalle.ts`),
   los tres gráficos nuevos de Resumen y el de la pestaña Seguimientos se cargan en el
   `constructor()` porque Resumen es la pestaña activa por defecto.
10. **No verificado visualmente en navegador**: esta sesión no tuvo acceso a una herramienta de
    navegador/captura de pantalla. El flujo de datos de los 8 usos de `<app-grafico>` (4 en
    `/tablero`, 1 en `/tablero/recursos`, 3 en el detalle de proyecto) se verificó end-to-end
    contra la API real de `seed_demo`, y `npm run build`/`npm run lint` confirman que el
    código compila y tipa correctamente, pero el renderizado real en pantalla (incluida la
    usabilidad a 400px) no se confirmó con una captura real.

## Adenda: "Proyectos por periodo" — horas plan vs. ejecutadas por proyecto, filtrable por semana o mes

Pedido por el usuario: una vista del Tablero con una fila por proyecto (horas plan vs.
ejecutadas) donde se pueda elegir semana o mes y navegar entre periodos, con una fila de
totales para ese periodo. No existía: `tabla_proyectos` da el histórico completo de cada
proyecto (sin fecha) y `ejecucion_mensual` da una serie fechada pero agregada de todos los
proyectos juntos (no una fila por proyecto).

### Diseño

- Nuevo `tabla_proyectos_por_periodo(proyectos, desde, hasta)` en `apps/tablero/services.py`:
  una fila por proyecto con `horas_plan` (prorrateada por intersección de días calendario entre
  cada `AsignacionRecurso` y `[desde, hasta]`) y `horas_ejec` (suma de `RegistroEjecucion`
  `APROBADO` cuyo `periodo_inicio` cae en el rango), más `totales` con la suma de todas las
  filas. Mismo alcance por rol que el resto del tablero (recibe `proyectos` ya acotado).
- El prorrateo necesitaba generalizarse: `prorratear_por_mes` (fase 06) solo prorratea contra
  un mes calendario completo, y una semana no es un mes — prorratear por mes sobrestimaría una
  semana suelta. Se extrajo `prorratear_por_rango(fecha_desde, fecha_hasta, valor_total,
  periodo_desde, periodo_hasta)` en `apps/core/calculos.py` con la intersección de días contra
  un rango arbitrario, y `prorratear_por_mes` ahora es ese mismo cálculo con el mes como
  periodo (refactor sin cambiar ningún resultado existente, con prueba que lo verifica).
- Nuevo `GET /tablero/proyectos-por-periodo/?desde=&hasta=` (`TablaProyectosPorPeriodoView`),
  mismo patrón de caché/alcance que los demás endpoints del tablero; `desde`/`hasta`
  obligatorios (no tiene sentido un "periodo" sin elegir uno). Se sumó también a
  `/tablero/exportar/?vista=proyectos-por-periodo`.
- Pantalla nueva `/tablero/proyectos-por-periodo`, con el mismo patrón de navegación
  Semanal/Mensual + «Anterior»/«Hoy»/«Siguiente» que ya usa "Mi registro de horas"
  (`apps/features/ejecucion/mi-registro`), en vez de un simple rango de fechas libre como
  `/tablero/recursos` — el pedido era explícitamente "seleccionar meses o semanas", no un
  rango arbitrario. Enlazada desde el panel principal del tablero.

### Evidencia

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/core apps/tablero -q
.............................................................................
126 passed

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec frontend npm run lint
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npx ng build
Application bundle generation complete.
```

## Adenda (fase 15): "Plan de costos" — plan vs. ejecutado de un proyecto, por mes y categoría, con horas y valor

Pedido por el usuario, a partir de una plantilla de Sheets de flujo de pagos mensual
(bloques Personal/Proveedores/Software-Licencias/Logística-Viáticos, con columnas por mes).
No existía en el código ninguna vista que combinara recursos + gastos no-personal **por mes
y por categoría** a la vez: `ejecucion_mensual` es mensual pero solo de personal;
`tabla_proyectos`/`resumen_global` combinan personal + no-personal pero sin desglose mensual
ni por categoría. Dos decisiones del usuario antes de construir: (1) un selector
Planeado/Ejecutado en vez de duplicar columnas por mes, y (2) los costos no-personal (sin
fecha propia) se reparten en partes iguales entre los meses del rango.

### Diseño

- Nuevo `plan_costos_proyecto(proyecto, desde=None, hasta=None)` en `apps/tablero/services.py`.
  Un bloque "Personal" (una fila por recurso, sumando todas sus asignaciones si tiene más de
  una; horas y valor prorrateados por mes con `prorratear_por_mes`, igual que
  `ejecucion_mensual`) y un bloque por cada `CategoriaRubro` con `RubroPresupuesto` en el
  proyecto (excluyendo `categoria=PERSONAL`, para no duplicar ese costo: ahí sale de
  `AsignacionRecurso`, no de un rubro). El `monto_planeado` de cada rubro no-personal se
  reparte en partes iguales entre los meses del rango (decisión confirmada; no hay fecha
  propia en `RubroPresupuesto` para prorratear de otra forma). Lo ejecutado no-personal agrupa
  `GastoEjecutado.monto` (`APROBADO`) por el mes de su `fecha`. Subtotal por bloque y total
  general (solo dinero) con el mismo helper `_armar_bloque`, para no repetir la acumulación.
- Nuevo `GET /tablero/plan-costos/?proyecto=&desde=&hasta=` (`PlanCostosProyectoView`):
  `proyecto` obligatorio (a diferencia del resto del tablero, que opera sobre un conjunto de
  proyectos), 404 si no existe o cae fuera del alcance por rol del usuario. Mismo patrón de
  caché que los demás endpoints. Se sumó a `/tablero/exportar/?vista=plan-costos` (de paso se
  corrigió que esa lista de vistas válidas no incluía "proyectos-por-periodo", un vacío previo
  a esta fase).
- Pantalla nueva `/tablero/plan-costos`: selector de proyecto obligatorio (nada se carga sin
  elegir uno) + selector segmentado Planeado/Ejecutado que no dispara otra petición — lee la
  misma respuesta ya cargada. Tabla con scroll horizontal, encabezado de dos niveles (mes →
  Horas/Valor), filas agrupadas por bloque con subtotal y fila de total general. Primera
  pantalla del tablero con columnas de mes en el encabezado — no había precedente de eso en el
  frontend (`proyectos-periodo` agrega un rango a un solo número, sin grilla mensual).

### Evidencia

```
$ docker compose -f infra/docker-compose.yml exec backend pytest apps/tablero -q
.........................................
41 passed

$ docker compose -f infra/docker-compose.yml exec backend pytest -q
516 passed

$ docker compose -f infra/docker-compose.yml exec backend ruff check .
All checks passed!

$ docker compose -f infra/docker-compose.yml exec backend python manage.py makemigrations --check --dry-run
No changes detected

$ docker compose -f infra/docker-compose.yml exec frontend npx ng lint
All files pass linting.

$ docker compose -f infra/docker-compose.yml exec frontend npx ng build
Application bundle generation complete.
```
