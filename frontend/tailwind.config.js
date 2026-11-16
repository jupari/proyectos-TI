/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        teal: {
          50: "#f0fdfb",
          100: "#e0f9f7",
          200: "#ccfbf1",
          300: "#99f6e4",
          400: "#5eead4",
          500: "#2dd4bf",
          600: "#14b8a6",
          700: "#0d9488",
          800: "#0f766e",
          900: "#134e4a",
        },
        // Mantener marca como alias para compatibilidad
        marca: {
          50: "#f0fdfb",
          100: "#e0f9f7",
          200: "#ccfbf1",
          300: "#99f6e4",
          400: "#5eead4",
          500: "#2dd4bf",
          600: "#14b8a6",
          700: "#0d9488",
          800: "#0f766e",
          900: "#134e4a",
        },
        neutro: {
          50: "#f8fafc",
          100: "#f1f5f9",
          200: "#e2e8f0",
          300: "#cbd5e1",
          400: "#94a3b8",
          500: "#64748b",
          600: "#475569",
          700: "#334155",
          800: "#1e293b",
          900: "#0f172a",
        },
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
        focus: "0 0 0 3px rgba(45, 212, 191, 0.1), 0 0 0 1px rgba(45, 212, 191, 0.5)",
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
