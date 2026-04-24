/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./main.jsx",
    "./App.jsx",
    "./components/**/*.{js,jsx}",
    "./features/**/*.{js,jsx}",
    "./hooks/**/*.{js,jsx}",
    "./pages/**/*.{js,jsx}",
    "./routes/**/*.{js,jsx}",
    "./services/**/*.{js,jsx}",
    "./utils/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        page: "var(--color-page)",
        card: "var(--color-card)",
        surface: "var(--color-surface)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        accent: "var(--color-accent)",
        "accent-soft": "var(--color-accent-soft)",
        border: "var(--color-border)",
        danger: "var(--color-danger)",
      },
      boxShadow: {
        soft: "0 18px 45px -25px rgba(14, 29, 23, 0.45)",
      },
      fontFamily: {
        sans: ["Manrope", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
