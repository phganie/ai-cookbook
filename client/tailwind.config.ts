import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0f766e",
          light: "#14b8a6",
          dark: "#115e59"
        }
      }
    }
  },
  plugins: []
};

export default config;


