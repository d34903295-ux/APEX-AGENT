import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// En Windows algunos entornos fallan la verificación TLS del proxy (unable to verify certificate).
// secure: false solo aplica al proxy de desarrollo, no al build de producción.
const devProxy = (target, rewrite) => ({
  target,
  changeOrigin: true,
  secure: false,
  ...(rewrite ? { rewrite } : {}),
});

export default defineConfig({
  plugins: [react()],
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "variables" as *;\n`,
        loadPaths: [path.resolve(__dirname, 'src/styles')],
      },
    },
  },
  server: {
    open: true,
    proxy: {
      '/api/mcp': devProxy('https://mcp.wallbit.io', (p) => p.replace(/^\/api\/mcp/, '/mcp')),
      '/api/wallbit': devProxy('https://api.wallbit.io', (p) => p.replace(/^\/api\/wallbit/, '/api/public/v1')),
      '/api/coingecko': devProxy('https://api.coingecko.com', (p) => p.replace(/^\/api\/coingecko/, '/api/v3')),
      '/api/fng': devProxy('https://api.alternative.me', (p) => p.replace(/^\/api\/fng/, '')),
      '/api/cryptonews': devProxy('https://min-api.cryptocompare.com', (p) => p.replace(/^\/api\/cryptonews/, '')),
    },
  },
});
