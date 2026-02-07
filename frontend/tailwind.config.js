/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{html,js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Professional Color Palette from Coolors
        neo: {
          navy: '#001524',       // Dark navy
          teal: '#15616D',       // Teal
          cream: '#FFECD1',      // Cream (background)
          orange: '#FF7D00',     // Orange (accent)
          maroon: '#78290F',     // Dark red/maroon
        },
        // Semantic aliases
        primary: '#FF7D00',
        secondary: '#15616D',
        accent: '#FF7D00',
        background: '#FFECD1',
        // Legacy colors for compatibility
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))'
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))'
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))'
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))'
        },
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      },
      boxShadow: {
        'neo': '4px 4px 0px 0px #001524',
        'neo-sm': '2px 2px 0px 0px #001524',
        'neo-lg': '6px 6px 0px 0px #001524',
        'neo-xl': '8px 8px 0px 0px #001524',
        'neo-hover': '2px 2px 0px 0px #001524',
        'neo-orange': '4px 4px 0px 0px #FF7D00',
        'neo-teal': '4px 4px 0px 0px #15616D',
      },
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      animation: {
        'shake': 'shake 0.5s ease-in-out',
        'marquee': 'marquee 20s linear infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '10%, 30%, 50%, 70%, 90%': { transform: 'translateX(-4px)' },
          '20%, 40%, 60%, 80%': { transform: 'translateX(4px)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}