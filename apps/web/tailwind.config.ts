import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background:          "hsl(var(--background))",
        foreground:          "hsl(var(--foreground))",
        card:                "hsl(var(--card))",
        "card-foreground":   "hsl(var(--card-foreground))",
        muted:               "hsl(var(--muted))",
        "muted-foreground":  "hsl(var(--muted-foreground))",
        border:              "hsl(var(--border))",
        primary:             "hsl(var(--primary))",
        "primary-light":     "hsl(var(--primary-light))",
        "primary-foreground":"hsl(var(--primary-foreground))",
        accent:              "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
        "card-md": "0 4px 12px 0 rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
      },
    },
  },
  plugins: [],
};

export default config;
