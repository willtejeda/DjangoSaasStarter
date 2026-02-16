/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': 'var(--bg)',
        'bg-elevated': 'var(--bg-elevated)',
        'bg-strong': 'var(--bg-strong)',
        'text-primary': 'var(--text-primary)',
        'text-muted': 'var(--text-muted)',
        'border-subtle': 'var(--border)',
        accent: 'var(--accent)',
        'accent-strong': 'var(--accent-strong)',
        signal: 'var(--signal)',
        ok: 'var(--ok)',
        warn: 'var(--warn)'
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Segoe UI', 'sans-serif'],
        heading: ['Newsreader', 'Georgia', 'serif'],
        mono: ['IBM Plex Mono', 'monospace']
      },
      boxShadow: {
        panel: 'var(--shadow)'
      }
    }
  },
  plugins: []
};
