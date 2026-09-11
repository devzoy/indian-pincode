// Build dist/ (CJS + ESM) from the ESM source.
//
// The data module (data/core-data.cjs) is shipped ONCE in dist/ and kept
// EXTERNAL from the bundles, so the ~KB payload is not duplicated across the CJS
// and ESM builds. Both entries import it via the relative path './core-data.cjs'.
// For a browser build, a consumer's bundler (esbuild/Vite/webpack) inlines that
// require, so nothing here uses Node built-ins.
import { build } from 'esbuild';
import { mkdirSync, copyFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, 'dist');
mkdirSync(dist, { recursive: true });

// Ship the single data module into dist.
copyFileSync(join(here, 'data', 'core-data.cjs'), join(dist, 'core-data.cjs'));

const common = {
  entryPoints: [join(here, 'src', 'index.mjs')],
  bundle: true,
  minify: true,
  platform: 'neutral',       // no Node built-ins
  target: ['es2020'],
  sourcemap: false,
  // Keep the data module external so it isn't inlined into each format's bundle.
  // The source imports '../data/core-data.cjs'; rewrite that specifier to the
  // sibling './core-data.cjs' that we copied into dist.
  external: ['*/core-data.cjs'],
  plugins: [{
    name: 'rewrite-data-path',
    setup(b) {
      b.onResolve({ filter: /core-data\.cjs$/ }, () => ({
        path: './core-data.cjs',
        external: true,
      }));
    },
  }],
};

await build({ ...common, format: 'esm', outfile: join(dist, 'index.mjs') });
await build({ ...common, format: 'cjs', outfile: join(dist, 'index.cjs') });

copyFileSync(join(here, 'src', 'index.d.ts'), join(dist, 'index.d.ts'));

console.log('[node-core] built dist/index.mjs, dist/index.cjs, dist/core-data.cjs, dist/index.d.ts');
