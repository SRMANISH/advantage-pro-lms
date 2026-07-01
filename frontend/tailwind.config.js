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
        navyDeep: "rgb(var(--color-navy-deep) / <alpha-value>)",
        aqua: "rgb(var(--color-aqua) / <alpha-value>)",
        logoRed: "rgb(var(--color-logo-red) / <alpha-value>)",
        logoYellow: "rgb(var(--color-logo-yellow) / <alpha-value>)",
        surfaceSoft: "rgb(var(--color-surface-soft) / <alpha-value>)",
        success: "rgb(var(--color-success) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)",
      },
      boxShadow: {
        card: "0 1px 2px rgb(15 31 58 / 0.04), 0 10px 28px rgb(15 31 58 / 0.06)",
        lift: "0 14px 40px rgb(15 31 58 / 0.14)",
        sidebar: "0 0 40px rgb(8 18 48 / 0.45)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "none" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.45s cubic-bezier(0.22,1,0.36,1) both",
      },
    },
  },
  plugins: [],
};
