/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#FFFFFF",
        panel: "#FFFFFF",
        accent: "#2563EB",
        copy: "#172033",
        muted: "#64748B",
        line: "#E2E8F0",
        wash: "#F1F5F9",
        success: "#456850",
        danger: "#9E3935",
        warning: "#8C5F27",
      },
      keyframes: {
        "slide-in": {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulse_dot: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
      animation: {
        "slide-in": "slide-in .25s ease-out",
        "pulse-dot": "pulse_dot 1s infinite",
      },
    },
  },
  plugins: [],
};
