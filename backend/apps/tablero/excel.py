"""Excel de las tareas con sus horas, para clasificarlas y sumarlas (hoja «Tareas»
con filtros y un total que sigue al filtro, y hoja «Resumen» con las sumas por
persona, proyecto, estado y sprint)."""

import io
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ENCABEZADO = PatternFill("solid", fgColor="0F766E")
NEGRITA_BLANCA = Font(bold=True, color="FFFFFF")
FORMATO_HORAS = "#,##0.00"

COLUMNAS = [
    ("Proyecto", 14),
    ("Nombre del proyecto", 32),
    ("Clave Jira", 13),
    ("Tarea", 48),
    ("Tipo", 12),
    ("Estado", 14),
    ("Épica", 28),
    ("Sprint", 16),
    ("Responsable", 24),
    ("Fecha fin plan", 14),
    ("Horas estimadas", 12),
    ("Horas en Jira", 12),
    ("Horas aprobadas en la app", 14),
]
COLUMNA_FECHA = 10
PRIMERA_COLUMNA_HORAS = 11


def _encabezar(hoja, fila, titulos):
    for columna, titulo in enumerate(titulos, start=1):
        celda = hoja.cell(row=fila, column=columna, value=titulo)
        celda.fill = ENCABEZADO
        celda.font = NEGRITA_BLANCA
        celda.alignment = Alignment(wrap_text=True, vertical="center")


def _hoja_tareas(libro, tareas):
    hoja = libro.active
    hoja.title = "Tareas"
    _encabezar(hoja, 1, [titulo for titulo, _ancho in COLUMNAS])
    for indice, (_titulo, ancho) in enumerate(COLUMNAS, start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho
    hoja.row_dimensions[1].height = 32

    base_jira = (settings.JIRA_BASE_URL or "").rstrip("/")
    for fila, tarea in enumerate(tareas, start=2):
        valores = [
            tarea.proyecto.codigo,
            tarea.proyecto.nombre,
            tarea.clave_jira or "",
            tarea.nombre,
            tarea.get_tipo_display(),
            tarea.get_estado_display(),
            tarea.epica_nombre,
            tarea.sprint.nombre if tarea.sprint else "",
            tarea.responsable.nombre if tarea.responsable else "Sin asignar",
            tarea.fecha_fin_plan,
            float(tarea.horas_estimadas),
            float(tarea.horas_jira),
            float(tarea.horas_ejecutadas),
        ]
        for columna, valor in enumerate(valores, start=1):
            celda = hoja.cell(row=fila, column=columna, value=valor)
            if columna == COLUMNA_FECHA:
                celda.number_format = "dd/mm/yyyy"
            elif columna >= PRIMERA_COLUMNA_HORAS:
                celda.number_format = FORMATO_HORAS
        if tarea.clave_jira and base_jira:
            hoja.cell(row=fila, column=3).hyperlink = f"{base_jira}/browse/{tarea.clave_jira}"

    ultima = max(len(tareas) + 1, 2)
    total = ultima + 2
    hoja.cell(row=total, column=COLUMNA_FECHA, value="Total visible").font = Font(bold=True)
    # SUBTOTAL ignora las filas ocultas por el filtro: el total sigue a lo que se ve.
    for columna in range(PRIMERA_COLUMNA_HORAS, PRIMERA_COLUMNA_HORAS + 3):
        letra = get_column_letter(columna)
        celda = hoja.cell(
            row=total, column=columna, value=f"=SUBTOTAL(109,{letra}2:{letra}{ultima})"
        )
        celda.font = Font(bold=True)
        celda.number_format = FORMATO_HORAS
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNAS))}{ultima}"


def _bloque(hoja, fila, titulo, clasificador, filas):
    hoja.cell(row=fila, column=1, value=titulo).font = Font(bold=True, size=12)
    _encabezar(
        hoja,
        fila + 1,
        [clasificador, "Tareas", "Horas estimadas", "Horas en Jira", "Horas aprobadas"],
    )
    actual = fila + 2
    for nombre, (cantidad, estimadas, jira, aprobadas) in sorted(filas.items()):
        hoja.cell(row=actual, column=1, value=nombre)
        hoja.cell(row=actual, column=2, value=cantidad)
        for columna, valor in ((3, estimadas), (4, jira), (5, aprobadas)):
            hoja.cell(row=actual, column=columna, value=float(valor)).number_format = (
                FORMATO_HORAS
            )
        actual += 1
    hoja.cell(row=actual, column=1, value="Total").font = Font(bold=True)
    for columna in range(2, 6):
        letra = get_column_letter(columna)
        celda = hoja.cell(
            row=actual,
            column=columna,
            value=f"=SUM({letra}{fila + 2}:{letra}{max(actual - 1, fila + 2)})",
        )
        celda.font = Font(bold=True)
        if columna > 2:
            celda.number_format = FORMATO_HORAS
    return actual + 2


def _acumular(tareas, clave_de):
    acumulado = defaultdict(lambda: [0, Decimal(0), Decimal(0), Decimal(0)])
    for tarea in tareas:
        fila = acumulado[clave_de(tarea)]
        fila[0] += 1
        fila[1] += tarea.horas_estimadas
        fila[2] += tarea.horas_jira
        fila[3] += tarea.horas_ejecutadas
    return {clave: tuple(valores) for clave, valores in acumulado.items()}


def _hoja_resumen(libro, tareas):
    hoja = libro.create_sheet("Resumen")
    hoja.column_dimensions["A"].width = 40
    for letra in "BCDE":
        hoja.column_dimensions[letra].width = 16
    hoja.cell(row=1, column=1, value="Horas por clasificación").font = Font(bold=True, size=14)
    hoja.cell(
        row=2,
        column=1,
        value="«Horas en Jira»: lo registrado en Jira. «Aprobadas»: lo aprobado en la aplicación.",
    )

    bloques = [
        (
            "Horas por responsable",
            "Responsable",
            lambda t: t.responsable.nombre if t.responsable else "Sin asignar",
        ),
        (
            "Horas por proyecto",
            "Proyecto",
            lambda t: f"{t.proyecto.codigo} — {t.proyecto.nombre}",
        ),
        ("Horas por estado", "Estado", lambda t: t.get_estado_display()),
        ("Horas por sprint", "Sprint", lambda t: t.sprint.nombre if t.sprint else "Sin sprint"),
    ]
    fila = 4
    for titulo, clasificador, clave_de in bloques:
        fila = _bloque(hoja, fila, titulo, clasificador, _acumular(tareas, clave_de))


def excel_de_tareas(tareas):
    """Bytes de un `.xlsx` con las tareas (instancias de `Tarea` ya con sus relaciones)."""
    libro = Workbook()
    _hoja_tareas(libro, tareas)
    _hoja_resumen(libro, tareas)
    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()
