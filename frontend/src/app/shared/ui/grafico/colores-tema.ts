/** Color de una variable del tema (canales RGB en `src/styles.css`).
 * Chart.js dibuja en `<canvas>` y no hereda CSS, así que se resuelve en cada
 * dibujo: pasar la función (no su resultado) como color del dataset. */
export function colorTema(variable: string): string {
  const canal = getComputedStyle(document.documentElement).getPropertyValue(`--${variable}`).trim();
  return canal ? `rgb(${canal})` : '#64748b';
}
