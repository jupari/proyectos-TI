"""Exportación a PDF del expediente (docs/plan/fase-09-seguimiento-expediente.md
§9.3.7). Si esto se complicara, el criterio de aceptación admite HTML
imprimible como alternativa — no hizo falta: `reportlab` con `Table`/
`Paragraph` cubre el expediente completo sin layouts complejos."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.core.choices import EstadoAprobacion, EstadoSeguimiento, EstadoTarea
from apps.tablero.services import resumen_ejecucion

ESTILOS = getSampleStyleSheet()


def _tabla(filas, encabezados, anchos=None):
    datos = [encabezados] + filas
    tabla = Table(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ]
        )
    )
    return tabla


def generar_pdf_expediente(proyecto, datos_expediente):
    """Devuelve los bytes del PDF: portada con datos y KPIs del proyecto,
    seguimientos publicados, resumen de tareas, resumen de ejecución e
    índice de documentos con sus versiones."""
    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        title=f"Expediente {proyecto.codigo}",
    )

    cuerpo = []
    cuerpo.append(Paragraph(f"Expediente digital — {proyecto.codigo}", ESTILOS["Title"]))
    cuerpo.append(Paragraph(proyecto.nombre, ESTILOS["Heading2"]))
    cuerpo.append(Spacer(1, 0.3 * cm))

    resumen = resumen_ejecucion(proyecto)
    nombre_lider = proyecto.lider_tecnico.nombre_completo if proyecto.lider_tecnico else "—"
    horas_plan_ejec = f"{resumen['horas_planeadas']} / {resumen['horas_ejecutadas']}"
    costo_plan_ejec = f"{resumen['costo_planeado']} / {resumen['costo_ejecutado']}"
    datos_portada = [
        ["Estado", proyecto.estado, "Prioridad", proyecto.prioridad],
        ["Gerente", proyecto.gerente.nombre_completo, "Líder técnico", nombre_lider],
        ["Inicio plan", str(proyecto.fecha_inicio_plan), "Fin plan", str(proyecto.fecha_fin_plan)],
        ["Horas plan / ejec.", horas_plan_ejec, "Semáforo", resumen["semaforo"]],
        ["Costo plan / ejec.", costo_plan_ejec, "Avance", f"{resumen['avance']}%"],
    ]
    anchos_portada = [3.5 * cm, 6 * cm, 3.5 * cm, 4 * cm]
    encabezados_portada = ["Campo", "Valor", "Campo", "Valor"]
    cuerpo.append(_tabla(datos_portada, encabezados_portada, anchos=anchos_portada))
    cuerpo.append(Spacer(1, 0.5 * cm))

    cuerpo.append(Paragraph("Seguimientos publicados", ESTILOS["Heading2"]))
    seguimientos = proyecto.seguimientos.filter(
        activo=True, estado=EstadoSeguimiento.PUBLICADO
    ).order_by("-periodo_inicio")
    filas_seguimiento = [
        [
            s.periodicidad,
            f"{s.periodo_inicio} a {s.periodo_fin}",
            str(s.fecha_corte),
            f"{s.avance_reportado}%",
            s.semaforo,
            s.publicado_por.nombre_completo if s.publicado_por else "—",
        ]
        for s in seguimientos
    ]
    if filas_seguimiento:
        cuerpo.append(
            _tabla(
                filas_seguimiento,
                ["Periodicidad", "Periodo", "Corte", "Avance", "Semáforo", "Publicado por"],
            )
        )
    else:
        cuerpo.append(Paragraph("Sin seguimientos publicados.", ESTILOS["Normal"]))
    cuerpo.append(Spacer(1, 0.5 * cm))

    cuerpo.append(Paragraph("Resumen de tareas", ESTILOS["Heading2"]))
    total_tareas = proyecto.tareas.filter(activo=True).count()
    completadas = proyecto.tareas.filter(activo=True, estado=EstadoTarea.COMPLETADA).count()
    vencidas = resumen["tareas_vencidas"]
    cuerpo.append(
        Paragraph(
            f"Total: {total_tareas} · Completadas: {completadas} · "
            f"Abiertas: {resumen['tareas_abiertas']} · Vencidas: {vencidas}",
            ESTILOS["Normal"],
        )
    )
    cuerpo.append(Spacer(1, 0.5 * cm))

    cuerpo.append(Paragraph("Resumen de ejecución", ESTILOS["Heading2"]))
    registros_aprobados = proyecto.registros_ejecucion.filter(
        activo=True, estado_aprobacion=EstadoAprobacion.APROBADO
    ).count()
    cuerpo.append(
        Paragraph(
            f"Horas aprobadas: {resumen['horas_ejecutadas']} ({resumen['pct_horas'] or 0:.1f}% "
            f"del plan) en {registros_aprobados} registro(s) · "
            f"Costo ejecutado: {resumen['costo_ejecutado']} "
            f"({resumen['pct_dinero'] or 0:.1f}% del plan).",
            ESTILOS["Normal"],
        )
    )
    cuerpo.append(Spacer(1, 0.5 * cm))

    cuerpo.append(Paragraph("Índice de documentos", ESTILOS["Heading2"]))
    filas_documentos = []
    for categoria, documentos in sorted(datos_expediente["documentos_por_categoria"].items()):
        for doc in documentos:
            filas_documentos.append(
                [
                    doc.nombre,
                    categoria,
                    f"v{doc.version}",
                    str(doc.creado_en.date()),
                    doc.creado_por.nombre_completo if doc.creado_por else "—",
                ]
            )
    if filas_documentos:
        encabezados_doc = ["Nombre", "Categoría", "Versión", "Fecha", "Subido por"]
        cuerpo.append(_tabla(filas_documentos, encabezados_doc))
    else:
        cuerpo.append(Paragraph("Sin documentos cargados.", ESTILOS["Normal"]))

    documento.build(cuerpo)
    return buffer.getvalue()
