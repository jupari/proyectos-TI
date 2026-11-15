"""Seis endpoints de solo lectura (docs/api-contrato.md §7): ninguno tiene
un modelo propio (toda la matemática vive en `apps/tablero/services.py`),
así que todos son `APIView`, no `ViewSet`. El alcance por rol y los filtros
de `/proyectos/` se resuelven una sola vez en `proyectos_del_tablero`
(`apps/tablero/filters.py`) y se le pasan a los servicios ya resueltos."""

import csv
import datetime
import io

from django.http import StreamingHttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .cache import desde_cache_o_calcular
from .filters import proyectos_del_tablero
from .services import (
    ejecucion_mensual,
    ocupacion_recursos,
    plan_costos_proyecto,
    resumen_global,
    resumen_tareas,
    tabla_proyectos,
    tabla_proyectos_por_periodo,
)

PARAMETROS_FILTRO_PROYECTO = [
    OpenApiParameter("estado", str, required=False),
    OpenApiParameter("prioridad", str, required=False),
    OpenApiParameter("portafolio", str, required=False),
    OpenApiParameter("area_solicitante", str, required=False),
    OpenApiParameter("gerente", str, required=False),
    OpenApiParameter("lider_tecnico", str, required=False),
    OpenApiParameter("semaforo", str, required=False),
    OpenApiParameter("mis_proyectos", bool, required=False),
    OpenApiParameter("refrescar", bool, required=False, description="Salta la caché de 60s."),
]


def _fecha(valor, nombre):
    try:
        return datetime.date.fromisoformat(valor)
    except ValueError as exc:
        raise ValidationError({nombre: ["Formato de fecha inválido, use AAAA-MM-DD."]}) from exc


def _rango_fechas(request, requerido):
    desde = request.query_params.get("desde")
    hasta = request.query_params.get("hasta")
    if requerido and not (desde and hasta):
        raise ValidationError({"desde": ["«desde» y «hasta» son obligatorios."]})

    desde = _fecha(desde, "desde") if desde else None
    hasta = _fecha(hasta, "hasta") if hasta else None
    if desde and hasta and desde > hasta:
        raise ValidationError({"desde": ["«desde» no puede ser posterior a «hasta»."]})
    return desde, hasta


class ResumenGlobalView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Tarjetas globales del tablero",
        description="docs/api-contrato.md §7: proyectos por estado y por semáforo, "
        "totales de horas y dinero plan vs. ejecutado, proyectos en riesgo, horas "
        "pendientes de aprobación, compromisos vencidos, hitos incumplidos. Respeta "
        "siempre el alcance por rol.",
        parameters=PARAMETROS_FILTRO_PROYECTO,
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)
        datos, calculado_en = desde_cache_o_calcular(
            request, "resumen", lambda: resumen_global(proyectos)
        )
        return Response({**datos, "calculado_en": calculado_en.isoformat()})


class TablaProyectosView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Una fila por proyecto con sus KPIs",
        description="docs/api-contrato.md §7: el bloque `resumen_ejecucion` completo "
        "por proyecto, filtrable igual que `/proyectos/`.",
        parameters=PARAMETROS_FILTRO_PROYECTO,
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)

        def calcular():
            filas = tabla_proyectos(proyectos)
            for fila in filas:
                fila["resumen_ejecucion"]["fecha_corte"] = fila["resumen_ejecucion"][
                    "fecha_corte"
                ].isoformat()
            return filas

        filas, calculado_en = desde_cache_o_calcular(request, "proyectos", calcular)
        return Response({"filas": filas, "calculado_en": calculado_en.isoformat()})


class EjecucionMensualView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Serie mensual de ejecución",
        description="docs/api-contrato.md §7: `[{mes, horas_plan, horas_ejec, costo_plan, "
        "costo_ejec, horas_ejec_acum, costo_ejec_acum}]`. `proyecto` acota a un solo "
        "proyecto; sin `desde`/`hasta` se usa el rango que cubren sus datos.",
        parameters=[
            *PARAMETROS_FILTRO_PROYECTO,
            OpenApiParameter("proyecto", str, required=False),
            OpenApiParameter("desde", str, required=False),
            OpenApiParameter("hasta", str, required=False),
        ],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)
        proyecto_id = request.query_params.get("proyecto")
        if proyecto_id:
            proyectos = proyectos.filter(id=proyecto_id)
        desde, hasta = _rango_fechas(request, requerido=False)

        serie, calculado_en = desde_cache_o_calcular(
            request, "ejecucion-mensual", lambda: ejecucion_mensual(proyectos, desde, hasta)
        )
        return Response({"serie": serie, "calculado_en": calculado_en.isoformat()})


class TablaProyectosPorPeriodoView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Horas plan vs. ejecutadas por proyecto en un periodo",
        description="docs/api-contrato.md §7: una fila por proyecto con sus horas "
        "planeadas y ejecutadas dentro de `desde`/`hasta` (p. ej. una semana o un mes "
        "elegidos a mano), más una fila de `totales` para ese mismo rango.",
        parameters=[
            *PARAMETROS_FILTRO_PROYECTO,
            OpenApiParameter("desde", str, required=True),
            OpenApiParameter("hasta", str, required=True),
        ],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)
        desde, hasta = _rango_fechas(request, requerido=True)

        datos, calculado_en = desde_cache_o_calcular(
            request,
            "proyectos-por-periodo",
            lambda: tabla_proyectos_por_periodo(proyectos, desde, hasta),
        )
        return Response({**datos, "calculado_en": calculado_en.isoformat()})


class PlanCostosProyectoView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Plan de costos de un proyecto, por mes y categoría",
        description="docs/api-contrato.md §7: costo planeado vs. ejecutado de UN "
        "proyecto, mes a mes, en un bloque «Personal» (una fila por recurso, con "
        "horas y valor) y un bloque por cada categoría de rubro con datos "
        "(solo valor). Sin `desde`/`hasta` se usa la planeación completa del "
        "proyecto (`fecha_inicio_plan`–`fecha_fin_plan`).",
        parameters=[
            OpenApiParameter("proyecto", str, required=True),
            OpenApiParameter("desde", str, required=False),
            OpenApiParameter("hasta", str, required=False),
        ],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyecto_id = request.query_params.get("proyecto")
        if not proyecto_id:
            raise ValidationError({"proyecto": ["Este parámetro es obligatorio."]})
        proyecto = proyectos_del_tablero(request).filter(id=proyecto_id).first()
        if proyecto is None:
            raise NotFound("El proyecto no existe o no está en su alcance.")
        desde, hasta = _rango_fechas(request, requerido=False)

        datos, calculado_en = desde_cache_o_calcular(
            request, "plan-costos", lambda: plan_costos_proyecto(proyecto, desde, hasta)
        )
        return Response({**datos, "calculado_en": calculado_en.isoformat()})


class RecursosOcupacionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ocupación de recursos en un rango",
        description="docs/api-contrato.md §7: horas planeadas, ejecutadas, capacidad y "
        "% de ocupación por recurso y mes, para los recursos con asignación en los "
        "proyectos del alcance del usuario.",
        parameters=[
            *PARAMETROS_FILTRO_PROYECTO,
            OpenApiParameter("desde", str, required=True),
            OpenApiParameter("hasta", str, required=True),
            OpenApiParameter("perfil", str, required=False),
        ],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)
        desde, hasta = _rango_fechas(request, requerido=True)
        perfil = request.query_params.get("perfil")

        recursos, calculado_en = desde_cache_o_calcular(
            request,
            "recursos",
            lambda: ocupacion_recursos(proyectos, desde, hasta, perfil),
        )
        return Response({"recursos": recursos, "calculado_en": calculado_en.isoformat()})


class TareasResumenView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Resumen de tareas del tablero",
        description="docs/api-contrato.md §7: conteo por estado, vencidas, creadas "
        "durante la ejecución y promedio de días de atraso. `proyecto` acota a un "
        "solo proyecto (p. ej. para la pestaña Resumen del detalle).",
        parameters=[*PARAMETROS_FILTRO_PROYECTO, OpenApiParameter("proyecto", str, required=False)],
        responses={200: {"type": "object"}},
    )
    def get(self, request):
        proyectos = proyectos_del_tablero(request)
        proyecto_id = request.query_params.get("proyecto")
        if proyecto_id:
            proyectos = proyectos.filter(id=proyecto_id)
        datos, calculado_en = desde_cache_o_calcular(
            request, "tareas", lambda: resumen_tareas(proyectos)
        )
        return Response({**datos, "calculado_en": calculado_en.isoformat()})


# --- Exportación CSV (fase 10 §10.1.4) ---------------------------------------


def _texto(valor):
    return "" if valor is None else str(valor)


def _filas_csv_proyectos(proyectos):
    encabezados = [
        "Código",
        "Nombre",
        "Gerente",
        "Estado",
        "% horas",
        "% dinero",
        "SPI",
        "CPI",
        "Desviación presupuestal",
        "Semáforo",
    ]
    filas = []
    for fila in tabla_proyectos(proyectos):
        r = fila["resumen_ejecucion"]
        filas.append(
            [
                fila["codigo"],
                fila["nombre"],
                _texto(fila["gerente"]),
                fila["estado"],
                _texto(r["pct_horas"]),
                _texto(r["pct_dinero"]),
                _texto(r["spi"]),
                _texto(r["cpi"]),
                _texto(r["desviacion_presupuestal"]),
                r["semaforo"],
            ]
        )
    return encabezados, filas


def _filas_csv_recursos(proyectos, request):
    desde, hasta = _rango_fechas(request, requerido=True)
    perfil = request.query_params.get("perfil")
    encabezados = [
        "Recurso",
        "Año",
        "Mes",
        "Horas planeadas",
        "Horas ejecutadas",
        "Capacidad",
        "% ocupación",
    ]
    filas = [
        [
            fila["recurso_nombre"],
            fila["anio"],
            fila["mes"],
            _texto(fila["horas_planeadas"]),
            _texto(fila["horas_ejecutadas"]),
            _texto(fila["capacidad"]),
            _texto(fila["pct_ocupacion"]),
        ]
        for fila in ocupacion_recursos(proyectos, desde, hasta, perfil)
    ]
    return encabezados, filas


def _filas_csv_proyectos_por_periodo(proyectos, request):
    desde, hasta = _rango_fechas(request, requerido=True)
    encabezados = ["Código", "Proyecto", "Horas plan", "Horas ejecutadas", "% consumo"]
    datos = tabla_proyectos_por_periodo(proyectos, desde, hasta)
    filas = [
        [
            fila["codigo"],
            fila["nombre"],
            _texto(fila["horas_plan"]),
            _texto(fila["horas_ejec"]),
            _texto(fila["pct_horas"]),
        ]
        for fila in datos["filas"]
    ]
    totales = datos["totales"]
    filas.append(
        [
            "",
            "Total",
            _texto(totales["horas_plan"]),
            _texto(totales["horas_ejec"]),
            _texto(totales["pct_horas"]),
        ]
    )
    return encabezados, filas


def _filas_csv_ejecucion_mensual(proyectos, request):
    desde, hasta = _rango_fechas(request, requerido=False)
    encabezados = [
        "Mes",
        "Horas plan",
        "Horas ejecutadas",
        "Costo plan",
        "Costo ejecutado",
        "Horas ejecutadas acumuladas",
        "Costo ejecutado acumulado",
    ]
    filas = [
        [
            fila["mes"],
            _texto(fila["horas_plan"]),
            _texto(fila["horas_ejec"]),
            _texto(fila["costo_plan"]),
            _texto(fila["costo_ejec"]),
            _texto(fila["horas_ejec_acum"]),
            _texto(fila["costo_ejec_acum"]),
        ]
        for fila in ejecucion_mensual(proyectos, desde, hasta)
    ]
    return encabezados, filas


def _filas_csv_plan_costos(proyectos, request):
    proyecto_id = request.query_params.get("proyecto")
    if not proyecto_id:
        raise ValidationError({"proyecto": ["Este parámetro es obligatorio."]})
    proyecto = proyectos.filter(id=proyecto_id).first()
    if proyecto is None:
        raise NotFound("El proyecto no existe o no está en su alcance.")
    desde, hasta = _rango_fechas(request, requerido=False)
    datos = plan_costos_proyecto(proyecto, desde, hasta)
    meses = datos["meses"]

    encabezados = ["Categoría", "Concepto"]
    for mes in meses:
        encabezados += [
            f"Horas plan {mes}",
            f"Valor plan {mes}",
            f"Horas ejec {mes}",
            f"Valor ejec {mes}",
        ]
    encabezados += ["Total horas plan", "Total valor plan", "Total horas ejec", "Total valor ejec"]

    def _renglon(etiqueta, concepto, por_mes, total):
        renglon = [etiqueta, concepto]
        for mes in meses:
            valores = por_mes[mes]
            renglon += [
                _texto(valores.get("horas_plan")),
                _texto(valores.get("valor_plan")),
                _texto(valores.get("horas_ejec")),
                _texto(valores.get("valor_ejec")),
            ]
        renglon += [
            _texto(total.get("horas_plan")),
            _texto(total.get("valor_plan")),
            _texto(total.get("horas_ejec")),
            _texto(total.get("valor_ejec")),
        ]
        return renglon

    filas = []
    for bloque in datos["bloques"]:
        for fila in bloque["filas"]:
            filas.append(
                _renglon(bloque["etiqueta"], fila["nombre"], fila["por_mes"], fila["total"])
            )
        subtotal = bloque["subtotal"]
        filas.append(
            _renglon(bloque["etiqueta"], "SUBTOTAL", subtotal["por_mes"], subtotal["total"])
        )
    total_general = datos["total_general"]
    filas.append(_renglon("", "TOTAL GENERAL", total_general["por_mes"], total_general["total"]))
    return encabezados, filas


_CONSTRUCTORES_CSV = {
    "proyectos": lambda proyectos, request: _filas_csv_proyectos(proyectos),
    "recursos": _filas_csv_recursos,
    "ejecucion-mensual": _filas_csv_ejecucion_mensual,
    "proyectos-por-periodo": _filas_csv_proyectos_por_periodo,
    "plan-costos": _filas_csv_plan_costos,
}


class ExportarTableroView(APIView):
    """`GET /tablero/exportar/?formato=csv&vista=proyectos|recursos|ejecucion-mensual`:
    `StreamingHttpResponse` con separador `;` y BOM UTF-8 (para que Excel en
    español lo abra bien), con los mismos filtros que la vista equivalente."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Exporta una vista del tablero a CSV",
        description="docs/api-contrato.md §7.",
        parameters=[
            *PARAMETROS_FILTRO_PROYECTO,
            OpenApiParameter("formato", str, required=True, enum=["csv"]),
            OpenApiParameter(
                "vista",
                str,
                required=True,
                enum=[
                    "proyectos",
                    "recursos",
                    "ejecucion-mensual",
                    "proyectos-por-periodo",
                    "plan-costos",
                ],
            ),
            OpenApiParameter("desde", str, required=False),
            OpenApiParameter("hasta", str, required=False),
            OpenApiParameter("perfil", str, required=False),
            OpenApiParameter("proyecto", str, required=False),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        formato = request.query_params.get("formato", "csv")
        vista = request.query_params.get("vista")
        if formato != "csv":
            raise ValidationError({"formato": ["Solo se soporta «csv»."]})
        constructor = _CONSTRUCTORES_CSV.get(vista)
        if constructor is None:
            raise ValidationError(
                {
                    "vista": [
                        "Debe ser «proyectos», «recursos», «ejecucion-mensual», "
                        "«proyectos-por-periodo» o «plan-costos»."
                    ]
                }
            )

        proyectos = proyectos_del_tablero(request)
        encabezados, filas = constructor(proyectos, request)

        def generar():
            buffer = io.StringIO()
            escritor = csv.writer(buffer, delimiter=";")
            buffer.write("﻿")
            escritor.writerow(encabezados)
            yield buffer.getvalue()
            for fila in filas:
                buffer.seek(0)
                buffer.truncate(0)
                escritor.writerow(fila)
                yield buffer.getvalue()

        respuesta = StreamingHttpResponse(generar(), content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = f'attachment; filename="tablero-{vista}.csv"'
        return respuesta
