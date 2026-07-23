import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0e14",
        surface: "#12161f",
        border: "#232838",
        accent: "#22d3a8",
        accentMuted: "#0f7a63",
        textPrimary: "#e6e9ef",
        textMuted: "#8b93a7",
      },
    },
  },
  plugins: [],
};

export default config;