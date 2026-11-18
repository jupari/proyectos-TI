import { EntregableHito, FaseProyecto, Hito } from '../../../../core/models';
import { avanceDeFase, construirLineaTiempo, hitoVencido, hoyIso, resumirLineaTiempo } from './linea-tiempo.utils';

const base = { activo: true, creado_en: '', actualizado_en: '', creado_por: null, actualizado_por: null };

function fase(parcial: Partial<FaseProyecto>): FaseProyecto {
  return {
    ...base, id: 'f', proyecto: 'p', nombre: 'Fase', orden: 1, peso: '50',
    fecha_inicio_plan: '2026-01-01', fecha_fin_plan: '2026-01-31', fecha_inicio_real: null,
    fecha_fin_real: null, estado: 'PENDIENTE', ...parcial,
  } as FaseProyecto;
}

function hito(parcial: Partial<Hito>): Hito {
  return {
    ...base, id: 'h', proyecto: 'p', nombre: 'Hito', descripcion: '', fecha_plan: '2026-01-15',
    fecha_real: null, estado: 'PENDIENTE', criterio_cumplimiento: '', es_entregable: false,
    entregables: [], ...parcial,
  } as Hito;
}

function entregable(estado: EntregableHito['estado']): EntregableHito {
  return { ...base, id: estado, proyecto: 'p', hito: 'h', nombre: 'E', descripcion: '', estado, fecha_entrega: null } as EntregableHito;
}

describe('linea-tiempo.utils', () => {
  it('ordena por fecha, con la fase antes que el hito en un empate, y coloca «hoy»', () => {
    const items = construirLineaTiempo(
      [fase({ id: 'f2', fecha_inicio_plan: '2026-03-01' }), fase({ id: 'f1', fecha_inicio_plan: '2026-01-01' })],
      [hito({ id: 'h1', fecha_plan: '2026-01-01' }), hito({ id: 'h2', fecha_plan: '2026-06-01' })],
      '2026-02-01',
    );

    expect(items.map((i) => (i.tipo === 'fase' ? i.fase.id : i.tipo === 'hito' ? i.hito.id : 'hoy'))).toEqual([
      'f1', 'h1', 'hoy', 'f2', 'h2',
    ]);
  });

  it('pone «hoy» al final si todo ya pasó y omite lo inactivo', () => {
    const items = construirLineaTiempo([], [hito({ fecha_plan: '2020-01-01' }), hito({ id: 'x', activo: false })], '2026-02-01');

    expect(items.map((i) => i.tipo)).toEqual(['hito', 'hoy']);
  });

  it('calcula el avance de la fase según su estado y el tiempo transcurrido', () => {
    const enCurso = fase({ estado: 'EN_PROGRESO', fecha_inicio_plan: '2026-01-01', fecha_fin_plan: '2026-01-11' });

    expect(avanceDeFase(fase({ estado: 'COMPLETADA' }), '2026-01-01')).toBe(100);
    expect(avanceDeFase(fase({ estado: 'PENDIENTE' }), '2026-01-20')).toBe(0);
    expect(avanceDeFase(enCurso, '2026-01-06')).toBe(50);
    expect(avanceDeFase(enCurso, '2027-01-01')).toBe(100);
  });

  it('marca como vencido solo un hito pendiente con fecha pasada', () => {
    expect(hitoVencido(hito({ fecha_plan: '2026-01-01' }), '2026-02-01')).toBe(true);
    expect(hitoVencido(hito({ fecha_plan: '2026-03-01' }), '2026-02-01')).toBe(false);
    expect(hitoVencido(hito({ fecha_plan: '2026-01-01', estado: 'CUMPLIDO' }), '2026-02-01')).toBe(false);
  });

  it('resume fases, hitos, entregables y el próximo hito', () => {
    const resumen = resumirLineaTiempo(
      [fase({ estado: 'COMPLETADA' }), fase({ id: 'f2' })],
      [
        hito({ id: 'a', estado: 'CUMPLIDO', entregables: [entregable('APROBADO'), entregable('PENDIENTE')] }),
        hito({ id: 'b', fecha_plan: '2026-01-10' }),
        hito({ id: 'c', fecha_plan: '2026-04-01' }),
        hito({ id: 'd', fecha_plan: '2026-03-01' }),
      ],
      '2026-02-01',
    );

    expect(resumen).toMatchObject({
      fasesCompletadas: 1, fasesTotal: 2, hitosCumplidos: 1, hitosTotal: 4, hitosVencidos: 1,
      entregablesListos: 1, entregablesTotal: 2,
    });
    expect(resumen.proximoHito?.id).toBe('d');
  });

  it('hoyIso usa la fecha local sin desfase de zona horaria', () => {
    expect(hoyIso(new Date(2026, 0, 5, 23, 30))).toBe('2026-01-05');
  });
});
