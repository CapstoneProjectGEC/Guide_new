/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        heritage: {
          gold: "#D4AF37",
          "gold-radiant": "#E5C058",
          brown: "#2C1810",
          soapstone: "#4A4A4A",
          ivory: "#FDFBF7",
          basalt: "#120E0C",
          "deep-stone": "#1C1614",
          "carved-basalt": "#241C1A",
          sandstone: "#F7F3EB",
          marble: "#F5EBE6",
          umber: "#665C54",
          stone: "#A89F91",
          forest: "#2D6A4F",
          terracotta: "#9B2226",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        kannada: [
          "Noto Sans Kannada",
          "Tunga",
          "Kedage",
          "Mallige",
          "sans-serif",
        ],
        display: [
          "Outfit",
          "Inter",
          "sans-serif",
        ],
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      boxShadow: {
        heritage: "0 4px 20px -2px rgba(44, 24, 16, 0.08)",
        "heritage-lg": "0 10px 30px -4px rgba(44, 24, 16, 0.12)",
        "gold-glow": "0 0 15px rgba(212, 175, 55, 0.3)",
      },
    },
  },
  plugins: [],
};
