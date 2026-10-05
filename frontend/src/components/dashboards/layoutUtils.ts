export interface ComponenteDashboard {
  id: string;
  type: string;
  config: any;
  x: number;
  y: number;
  w: number;
  h: number;
  width?: number;
}

let contador = 0;

export function gerarId(): string {
  contador += 1;
  return `c${Date.now().toString(36)}${contador.toString(36)}`;
}

export const LARGURA_PADRAO = 6;
export const ALTURA_PADRAO = 3;

/**
 * Aceita layout plano [{type, config, width}] legado, plano com geometria
 * [{id, type, config, x, y, w, h}] ou aninhado [{components: [...]}].
 * Retorna sempre a forma completa com ids e geometria.
 */
export function normalizarComponentes(layout: any): ComponenteDashboard[] {
  const bruto: any[] = Array.isArray(layout)
    ? (layout as any[]).flatMap((item: any) =>
        Array.isArray(item?.components) ? item.components : [item]
      )
    : [];

  let cursorX = 0;
  let cursorY = 0;

  return bruto.map((item, idx) => {
    const w = Math.max(1, Math.min(Number(item?.w ?? item?.width ?? LARGURA_PADRAO) || LARGURA_PADRAO, 12));
    const h = Math.max(1, Number(item?.h ?? ALTURA_PADRAO) || ALTURA_PADRAO);

    const comp: ComponenteDashboard = {
      id:
        typeof item?.id === 'string' && item.id
          ? item.id
          : `auto-${idx}-${Math.random().toString(36).slice(2, 8)}`,
      type: String(item?.type ?? 'kpi'),
      config: item?.config ?? {},
      x: Number.isFinite(Number(item?.x)) ? Number(item.x) : 0,
      y: Number.isFinite(Number(item?.y)) ? Number(item.y) : 0,
      w,
      h,
      width: w,
    };

    if (!Number.isFinite(Number(item?.x)) || !Number.isFinite(Number(item?.y))) {
      if (cursorX + w > 12) {
        cursorX = 0;
        cursorY += h;
      }
      comp.x = cursorX;
      comp.y = cursorY;
    }
    cursorX = comp.x + w;

    return comp;
  });
}

export function paraLayoutSalvo(componentes: ComponenteDashboard[]) {
  return componentes.map(({ id, type, config, x, y, w, h, width }) => ({
    id, type, config, x, y, w, h, width,
  }));
}

export function paraGrid(componentes: ComponenteDashboard[]) {
  return componentes.map((c) => ({ i: c.id, x: c.x, y: c.y, w: c.w, h: c.h }));
}
