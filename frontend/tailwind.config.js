/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand tokens are CSS variables (RGB channels) so the theme is swappable / white-label ready.
        brand: {
          DEFAULT: "rgb(var(--color-brand) / <alpha-value>)",
          strong: "rgb(var(--color-brand-strong) / <alpha-value>)",
        },
        sky: "rgb(var(--color-sky) / <alpha-value>)",
        navy: "rgb(var(--color-navy) / <alpha-value>)",
        violet: "rgb(var(--color-violet) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        appbg: "rgb(var(--color-bg) / <alpha-value>)",
        brdr: "rgb(var(--color-border) / <alpha-value>)",
        ink: "rgb(var(--color-text) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};
