/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Paleta de marca (índigo). Centralizada para re-tematizar fácil.
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
        // Azul-tinta para superficies oscuras (sidebar, hero).
        ink: {
          50: "#eef0f7",
          100: "#d8deef",
          200: "#b4bedb",
          300: "#8593bd",
          400: "#5c6aa0",
          500: "#3f4d80",
          600: "#2f3a64",
          700: "#232c4c",
          800: "#1a2140",
          900: "#121634",
          950: "#0b0e22",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px 0 rgb(16 24 40 / 0.04), 0 1px 3px 0 rgb(16 24 40 / 0.06)",
        card: "0 1px 3px rgb(16 24 40 / 0.05), 0 6px 16px -6px rgb(16 24 40 / 0.08)",
        pop: "0 12px 32px -8px rgb(16 24 40 / 0.16), 0 4px 10px -4px rgb(16 24 40 / 0.10)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #34d399 0%, #059669 100%)",
        "ink-gradient": "linear-gradient(180deg, #161b3d 0%, #0b0e22 100%)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: { "fade-in": "fade-in 0.25s ease-out both" },
    },
  },
  plugins: [],
};
