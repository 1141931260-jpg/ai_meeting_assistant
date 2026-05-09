/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f0d05",
        gold: "#c79a34",
        paper: "#f3eadb",
        panel: "#fffaf1"
      }
    }
  },
  plugins: []
};
