/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{html,js,jsx}"],
    theme: {
        extend: {
            colors: {
                neo: {
                    navy: '#001524',
                    teal: '#15616D',
                    cream: '#FFECD1',
                    orange: '#FF7D00',
                    maroon: '#78290F',
                },
            },
            fontFamily: {
                heading: ['Space Grotesk', 'sans-serif'],
                body: ['Inter', 'sans-serif'],
            },
            boxShadow: {
                'neo': '4px 4px 0px 0px #001524',
                'neo-sm': '2px 2px 0px 0px #001524',
                'neo-lg': '6px 6px 0px 0px #001524',
            },
        },
    },
    plugins: [],
}
