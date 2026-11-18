import { Periodicidad, Seguimiento } from '../../../../core/models';

export interface SeguimientoVista {
  seguimiento: Seguimiento;
  /** Etiqueta grande del periodo: «Semana 46», «Noviembre», «17 nov». */
  etiqueta: string;
  /** Año del periodo, para el bloque de fecha. */
  anio: number;
  /** Texto completo: «10 – 16 nov 2026», «Noviembre 2026», «17 de noviembre de 2026». */
  titulo: string;
  /** Puntos de avance respecto al seguimiento anterior del mismo grupo; `null` si es el primero. */
  variacion: number | null;
}

export interface GrupoSeguimientos {
  periodicidad: Periodicidad;
  titulo: string;
  items: SeguimientoVista[];
  ultimoAvance: number;
}

const MESES = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
];

const TITULO_GRUPO: Record<Periodicidad, string> = {
  SEMANAL: 'Seguimientos semanales',
  MENSUAL: 'Seguimientos mensuales',
  DIARIA: 'Seguimientos diarios',
};

function partes(fechaIso: string): { anio: number; mes: number; dia: number } {
  const [anio, mes, dia] = fechaIso.slice(0, 10).split('-').map(Number);
  return { anio, mes, dia };
}

const abreviado = (mes: number): string => MESES[mes - 1].slice(0, 3);
const capitalizar = (texto: string): string => texto.charAt(0).toUpperCase() + texto.slice(1);

/** Semana ISO 8601 (la que contiene el jueves de esa semana). */
export function semanaIso(fechaIso: string): number {
  const { anio, mes, dia } = partes(fechaIso);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  const diaSemana = fecha.getUTCDay() || 7;
  fecha.setUTCDate(fecha.getUTCDate() + 4 - diaSemana);
  const inicioAnio = Date.UTC(fecha.getUTCFullYear(), 0, 1);
  return Math.ceil(((fecha.getTime() - inicioAnio) / 86_400_000 + 1) / 7);
}

function describir(s: Seguimiento): Pick<SeguimientoVista, 'etiqueta' | 'titulo' | 'anio'> {
  const inicio = partes(s.periodo_inicio);
  const fin = partes(s.periodo_fin);

  if (s.periodicidad === 'MENSUAL') {
    const mes = capitalizar(MESES[inicio.mes - 1]);
    return { etiqueta: mes.slice(0, 3), titulo: `${mes} ${inicio.anio}`, anio: inicio.anio };
  }
  if (s.periodicidad === 'SEMANAL') {
    const rango =
      inicio.mes === fin.mes
        ? `${inicio.dia} – ${fin.dia} ${abreviado(fin.mes)}`
        : `${inicio.dia} ${abreviado(inicio.mes)} – ${fin.dia} ${abreviado(fin.mes)}`;
    return {
      etiqueta: `Sem ${semanaIso(s.periodo_inicio)}`,
      titulo: `${rango} ${fin.anio}`,
      anio: fin.anio,
    };
  }
  return {
    etiqueta: `${inicio.dia} ${abreviado(inicio.mes)}`,
    titulo: `${inicio.dia} de ${MESES[inicio.mes - 1]} de ${inicio.anio}`,
    anio: inicio.anio,
  };
}

/** Agrupa por periodicidad (el grupo con el seguimiento más reciente va
 * primero) y ordena cada grupo del más reciente al más antiguo, calculando
 * cuánto subió o bajó el avance frente al periodo anterior. */
export function agruparSeguimientos(seguimientos: readonly Seguimiento[]): GrupoSeguimientos[] {
  const porPeriodicidad = new Map<Periodicidad, Seguimiento[]>();
  for (const s of seguimientos.filter((x) => x.activo)) {
    porPeriodicidad.set(s.periodicidad, [...(porPeriodicidad.get(s.periodicidad) ?? []), s]);
  }

  const grupos = [...porPeriodicidad.entries()].map(([periodicidad, lista]): GrupoSeguimientos => {
    const ascendente = [...lista].sort((a, b) => a.periodo_inicio.localeCompare(b.periodo_inicio));
    const items = ascendente
      .map((seguimiento, i): SeguimientoVista => ({
        seguimiento,
        ...describir(seguimiento),
        variacion:
          i === 0
            ? null
            : Number(seguimiento.avance_reportado) - Number(ascendente[i - 1].avance_reportado),
      }))
      .reverse();
    return {
      periodicidad,
      titulo: TITULO_GRUPO[periodicidad],
      items,
      ultimoAvance: Number(items[0].seguimiento.avance_reportado),
    };
  });

  return grupos.sort((a, b) =>
    b.items[0].seguimiento.periodo_inicio.localeCompare(a.items[0].seguimiento.periodo_inicio),
  );
}
