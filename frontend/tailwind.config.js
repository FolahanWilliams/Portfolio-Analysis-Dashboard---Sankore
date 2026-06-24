/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: "#102a43",
          50: "#eef3f9",
          700: "#1c3d5e",
          800: "#14324f",
          900: "#091d31",
        },
        brand: {
          DEFAULT: "#2563eb",
          light: "#60a5fa",
        },
        positive: "#059669",
        negative: "#dc2626",
        surface: "#eef2f8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Calibri", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
