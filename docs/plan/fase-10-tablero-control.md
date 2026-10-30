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

- [ ] Tras el login, `/tablero` muestra los KPIs globales del alcance del usuario.
- [ ] Los totales del tablero cuadran con la suma de los proyectos listados.
- [ ] Un `LIDER` ve en el tablero solo sus proyectos y sus totales son consistentes.
- [ ] Cada tarjeta de KPI enlaza a la lista ya filtrada.
- [ ] Los cuatro gráficos se pintan con los datos de `seed_demo` y tienen su tabla equivalente
      accesible para lector de pantalla.
- [ ] El proyecto en sobrecosto de `seed_demo` aparece en rojo, con CPI menor que 1.
- [ ] Un proyecto sin asignaciones muestra `—` en sus porcentajes, no 0%.
- [ ] La exportación a CSV abre correctamente en Excel en español, con los filtros aplicados.
- [ ] Aprobar un registro de ejecución y refrescar el tablero muestra el nuevo valor.
- [ ] `tabla_proyectos` cumple el límite de consultas con 50 proyectos.
- [ ] El tablero es usable a 400px de ancho.
- [ ] `pytest` verde, `ruff` limpio, `npm run build` y `npm run lint` limpios.

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

<!-- Pega aquí la salida real de los comandos de verificación. -->
