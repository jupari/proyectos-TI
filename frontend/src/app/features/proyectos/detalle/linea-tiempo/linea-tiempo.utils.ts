import { FaseProyecto, Hito } from '../../../../core/models';

export type ItemLineaTiempo =
  | { tipo: 'fase'; fecha: string; fase: FaseProyecto }
  | { tipo: 'hito'; fecha: string; hito: Hito }
  | { tipo: 'hoy'; fecha: string };

/** Fecha local de hoy como `YYYY-MM-DD` (no `toISOString`, que usa UTC y
 * en America/Bogota adelanta el día después de las 19:00). */
export function hoyIso(ahora = new Date()): string {
  const mes = String(ahora.getMonth() + 1).padStart(2, '0');
  const dia = String(ahora.getDate()).padStart(2, '0');
  return `${ahora.getFullYear()}-${mes}-${dia}`;
}

/** Mezcla fases (por su inicio) e hitos (por su fecha plan) en orden
 * cronológico, con la marca «hoy» en su sitio. En un empate la fase va antes
 * que el hito: el hito suele cerrar la fase. Las fechas son ISO
 * (`YYYY-MM-DD`), así que comparar como texto equivale a comparar fechas. */
export function construirLineaTiempo(
  fases: readonly FaseProyecto[],
  hitos: readonly Hito[],
  hoy: string,
): ItemLineaTiempo[] {
  const items: ItemLineaTiempo[] = [
    ...fases
      .filter((f) => f.activo)
      .map((fase): ItemLineaTiempo => ({ tipo: 'fase', fecha: fase.fecha_inicio_plan, fase })),
    ...hitos
      .filter((h) => h.activo)
      .map((hito): ItemLineaTiempo => ({ tipo: 'hito', fecha: hito.fecha_plan, hito })),
  ];
  const rango = (item: ItemLineaTiempo): number => (item.tipo === 'fase' ? 0 : 1);
  items.sort((a, b) => a.fecha.localeCompare(b.fecha) || rango(a) - rango(b));

  const posicionHoy = items.findIndex((item) => item.fecha > hoy);
  const marca: ItemLineaTiempo = { tipo: 'hoy', fecha: hoy };
  if (posicionHoy === -1) {
    items.push(marca);
  } else {
    items.splice(posicionHoy, 0, marca);
  }
  return items;
}

function aDias(fechaIso: string): number {
  const [anio, mes, dia] = fechaIso.slice(0, 10).split('-').map(Number);
  return Date.UTC(anio, mes - 1, dia) / 86_400_000;
}

/** Avance de una fase en el tiempo (0–100): completada = 100, pendiente = 0,
 * en progreso = fracción transcurrida entre su inicio y fin planeados. */
export function avanceDeFase(fase: FaseProyecto, hoy: string): number {
  if (fase.estado === 'COMPLETADA') return 100;
  if (fase.estado === 'PENDIENTE') return 0;
  const inicio = aDias(fase.fecha_inicio_plan);
  const fin = aDias(fase.fecha_fin_plan);
  if (fin <= inicio) return 50;
  const fraccion = (aDias(hoy) - inicio) / (fin - inicio);
  return Math.round(Math.min(1, Math.max(0, fraccion)) * 100);
}

/** Un hito pendiente cuya fecha plan ya pasó se presenta como vencido. */
export function hitoVencido(hito: Hito, hoy: string): boolean {
  return hito.estado === 'PENDIENTE' && hito.fecha_plan < hoy;
}

export interface ResumenLineaTiempo {
  fasesCompletadas: number;
  fasesTotal: number;
  hitosCumplidos: number;
  hitosTotal: number;
  hitosVencidos: number;
  entregablesListos: number;
  entregablesTotal: number;
  proximoHito: Hito | null;
}

export function resumirLineaTiempo(
  fases: readonly FaseProyecto[],
  hitos: readonly Hito[],
  hoy: string,
): ResumenLineaTiempo {
  const fasesActivas = fases.filter((f) => f.activo);
  const hitosActivos = hitos.filter((h) => h.activo);
  const entregables = hitosActivos.flatMap((h) => h.entregables ?? []);
  const proximos = hitosActivos
    .filter((h) => h.estado === 'PENDIENTE' && h.fecha_plan >= hoy)
    .sort((a, b) => a.fecha_plan.localeCompare(b.fecha_plan));
  return {
    fasesCompletadas: fasesActivas.filter((f) => f.estado === 'COMPLETADA').length,
    fasesTotal: fasesActivas.length,
    hitosCumplidos: hitosActivos.filter((h) => h.estado === 'CUMPLIDO').length,
    hitosTotal: hitosActivos.length,
    hitosVencidos: hitosActivos.filter((h) => hitoVencido(h, hoy) || h.estado === 'INCUMPLIDO')
      .length,
    entregablesListos: entregables.filter((e) => e.estado !== 'PENDIENTE').length,
    entregablesTotal: entregables.length,
    proximoHito: proximos[0] ?? null,
  };
}
