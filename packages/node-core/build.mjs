// Build dist/ (CJS + ESM) from the ESM source, inlining the embedded data.
// Also copies the hand-written .d.ts. Requires esbuild (devDependency).
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
  platform: 'neutral',   // no Node built-ins
  target: ['es2020'],
  sourcemap: false,
};

await build({ ...common, format: 'esm', outfile: join(dist, 'index.mjs') });
await build({ ...common, format: 'cjs', outfile: join(dist, 'index.cjs') });

copyFileSync(join(here, 'src', 'index.d.ts'), join(dist, 'index.d.ts'));

console.log('[node-core] built dist/index.mjs, dist/index.cjs, dist/index.d.ts');
