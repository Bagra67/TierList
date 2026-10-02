import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// https://vite.dev/config/ — https://vitest.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // /api/hello -> http://127.0.0.1:8000/hello (backend FastAPI)
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
