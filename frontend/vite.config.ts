import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// https://vite.dev/config/ — https://vitest.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // @/… -> src/… (alias attendu par les composants shadcn/ui)
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // Écoute en IPv4 sur la boucle locale. Par défaut, Vite écoute sur « localhost », que Node
    // résout en ::1 seulement : sous Windows, Firefox essaie d'abord 127.0.0.1 et attend ~2 s
    // le refus avant de basculer sur ::1, à chaque nouvelle connexion. 127.0.0.1 reste rapide
    // dans tous les navigateurs, sans exposer le serveur au réseau comme '::' ou true.
    host: '127.0.0.1',
    proxy: {
      // /api/auth/me -> http://127.0.0.1:8000/auth/me (backend FastAPI)
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**', 'src/main.tsx'],
      reporter: ['text', 'json-summary'],
    },
  },
});
