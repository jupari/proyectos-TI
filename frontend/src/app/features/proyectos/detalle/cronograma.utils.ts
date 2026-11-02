/** Utilidades puras para el Gantt de solo lectura de la pestaña Cronograma
 * (docs/plan/fase-07-tareas-programacion.md §7.3.11): construido con CSS
 * Grid, sin librería externa. Cada "periodo" es una columna de la grilla. */

export interface PeriodoCronograma {
  inicio: Date;
  fin: Date;
  etiqueta: string;
}

function aFechaUtc(iso: string): Date {
  const [anio, mes, dia] = iso.split('-').map(Number);
  return new Date(Date.UTC(anio, mes - 1, dia));
}

function inicioDeSemana(fecha: Date): Date {
  const copia = new Date(fecha);
  const diaSemana = copia.getUTCDay();
  const desplazamiento = diaSemana === 0 ? 6 : diaSemana - 1; // semana ISO: lunes primero
  copia.setUTCDate(copia.getUTCDate() - desplazamiento);
  return copia;
}

export function construirPeriodosSemana(minimo: Date, maximo: Date): PeriodoCronograma[] {
  const periodos: PeriodoCronograma[] = [];
  let cursor = inicioDeSemana(minimo);
  while (cursor <= maximo) {
    const fin = new Date(cursor);
    fin.setUTCDate(fin.getUTCDate() + 6);
    periodos.push({
      inicio: new Date(cursor),
      fin,
      etiqueta: `${cursor.getUTCDate()}/${cursor.getUTCMonth() + 1}`,
    });
    cursor = new Date(cursor);
    cursor.setUTCDate(cursor.getUTCDate() + 7);
  }
  return periodos;
}

const MESES_CORTOS = [
  'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
];

export function construirPeriodosMes(minimo: Date, maximo: Date): PeriodoCronograma[] {
  const periodos: PeriodoCronograma[] = [];
  let cursor = new Date(Date.UTC(minimo.getUTCFullYear(), minimo.getUTCMonth(), 1));
  while (cursor <= maximo) {
    const fin = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 0));
    periodos.push({
      inicio: new Date(cursor),
      fin,
      etiqueta: `${MESES_CORTOS[cursor.getUTCMonth()]} ${cursor.getUTCFullYear()}`,
    });
    cursor = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1));
  }
  return periodos;
}

/** Índice de columna de grilla (base 1, como exige `grid-column`) del
 * periodo que contiene `fechaIso`. Recorta al primer/último periodo si la
 * fecha cae fuera del rango construido. */
export function columnaDeFecha(fechaIso: string, periodos: PeriodoCronograma[]): number {
  const fecha = aFechaUtc(fechaIso);
  for (let i = 0; i < periodos.length; i++) {
    if (fecha >= periodos[i].inicio && fecha <= periodos[i].fin) {
      return i + 1;
    }
  }
  return fecha < periodos[0]?.inicio ? 1 : periodos.length;
}

export function rangoFechasDe(fechas: (string | null)[]): { minimo: Date; maximo: Date } | null {
  const validas = fechas.filter((f): f is string => !!f).map(aFechaUtc);
  if (validas.length === 0) return null;
  return {
    minimo: new Date(Math.min(...validas.map((d) => d.getTime()))),
    maximo: new Date(Math.max(...validas.map((d) => d.getTime()))),
  };
}
