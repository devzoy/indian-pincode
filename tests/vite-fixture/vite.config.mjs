import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  build: {
    lib: {
      entry: join(here, 'index.mjs'),
      formats: ['es'],
      fileName: 'bundle',
    },
    outDir: join(here, 'dist'),
    // Fail the build if a Node built-in sneaks in (browser target).
    rollupOptions: {
      external: [],
    },
    minify: false,
  },
});
