/** @type {import('tailwindcss').Config} */
const canal = (nombre) => `rgb(var(--${nombre}) / <alpha-value>)`;
const escala = (prefijo) =>
  Object.fromEntries(
    [50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((n) => [n, canal(`${prefijo}-${n}`)]),
  );

// Los colores salen de variables CSS (src/styles.css) para poder cambiar de
// tema y de modo claro/oscuro en tiempo de ejecución sin recompilar.
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        primario: escala("primario"),
        neutro: escala("neutro"),
        boton: { DEFAULT: canal("boton"), hover: canal("boton-hover") },
        surface: canal("surface"),
        exito: "#10b981",
        alerta: "#f59e0b",
        peligro: "#ef4444",
        semaforo: {
          verde: "#10b981",
          amarillo: "#f59e0b",
          rojo: "#ef4444",
        },
      },
      borderRadius: {
        panel: "0.75rem",
        input: "0.5rem",
      },
      boxShadow: {
        tarjeta: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        hover: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        focus: "0 0 0 3px rgb(var(--primario-500) / 0.15), 0 0 0 1px rgb(var(--primario-500) / 0.5)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
