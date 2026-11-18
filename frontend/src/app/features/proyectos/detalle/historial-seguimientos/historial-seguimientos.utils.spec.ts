import { Seguimiento } from '../../../../core/models';
import { agruparSeguimientos, semanaIso } from './historial-seguimientos.utils';

function seguimiento(parcial: Partial<Seguimiento>): Seguimiento {
  return {
    activo: true, id: 's', proyecto: 'p', periodicidad: 'SEMANAL', periodo_inicio: '2026-11-09',
    periodo_fin: '2026-11-15', avance_reportado: '10', ...parcial,
  } as Seguimiento;
}

describe('historial-seguimientos.utils', () => {
  it('calcula la semana ISO', () => {
    expect(semanaIso('2026-01-01')).toBe(1);
    expect(semanaIso('2026-11-09')).toBe(46);
    expect(semanaIso('2027-01-01')).toBe(53);
  });

  it('agrupa por periodicidad, ordena del más reciente al más antiguo y calcula la variación', () => {
    const grupos = agruparSeguimientos([
      seguimiento({ id: 'a', periodo_inicio: '2026-11-02', periodo_fin: '2026-11-08', avance_reportado: '20' }),
      seguimiento({ id: 'b', periodo_inicio: '2026-11-09', periodo_fin: '2026-11-15', avance_reportado: '35' }),
      seguimiento({ id: 'm', periodicidad: 'MENSUAL', periodo_inicio: '2026-10-01', periodo_fin: '2026-10-31', avance_reportado: '50' }),
    ]);

    expect(grupos.map((g) => g.periodicidad)).toEqual(['SEMANAL', 'MENSUAL']);
    const semanal = grupos[0];
    expect(semanal.items.map((i) => i.seguimiento.id)).toEqual(['b', 'a']);
    expect(semanal.items.map((i) => i.variacion)).toEqual([15, null]);
    expect(semanal.ultimoAvance).toBe(35);
    expect(grupos[1].items[0]).toMatchObject({ etiqueta: 'Oct', titulo: 'Octubre 2026', variacion: null });
  });

  it('describe el rango de una semana, también cuando cruza de mes', () => {
    const [grupo] = agruparSeguimientos([
      seguimiento({ id: 'x', periodo_inicio: '2026-11-30', periodo_fin: '2026-12-06' }),
      seguimiento({ id: 'y', periodo_inicio: '2026-11-09', periodo_fin: '2026-11-15' }),
    ]);

    expect(grupo.items[0].titulo).toBe('30 nov – 6 dic 2026');
    expect(grupo.items[1].titulo).toBe('9 – 15 nov 2026');
    expect(grupo.items[1].etiqueta).toBe('Sem 46');
  });
});
