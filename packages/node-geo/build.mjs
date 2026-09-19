// Build dist/ (CJS + ESM) for the geo package. Node built-ins and the core
// package stay external; data JSON is loaded at runtime from ../data (not bundled).
import { build } from 'esbuild';
import { mkdirSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, 'dist');
mkdirSync(dist, { recursive: true });

const common = {
  entryPoints: [join(here, 'src', 'index.mjs')],
  bundle: true,
  minify: true,
  platform: 'node',
  target: ['node18'],
  // Keep the core package and Node built-ins external.
  external: ['@devzoy/indian-pincode', 'node:*'],
  sourcemap: false,
};

await build({ ...common, format: 'esm', outfile: join(dist, 'index.mjs') });
await build({ ...common, format: 'cjs', outfile: join(dist, 'index.cjs') });

copyFileSync(join(here, 'src', 'index.d.ts'), join(dist, 'index.d.ts'));

console.log('[node-geo] built dist/index.mjs, dist/index.cjs, dist/index.d.ts');
