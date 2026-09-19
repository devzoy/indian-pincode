#!/usr/bin/env node
// Execute every ```javascript/```js README block as a whole, capturing each
// console.log call, and assert it matches the `// =>` marker on that source line.
// require()/import of the published names resolve to the locally built dist.
// Exits 1 on any error or mismatch.
import { execFileSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

const blocks = JSON.parse(
  execFileSync(PYTHON, [join(ROOT, 'tests', 'readme', 'extract_blocks.py'), 'node'],
    { encoding: 'utf8' })
);

const core = (await import(pathToFileURL(join(ROOT, 'packages/node-core/dist/index.mjs')))).default;
const geo = (await import(pathToFileURL(join(ROOT, 'packages/node-geo/dist/index.mjs')))).default;

function fakeRequire(spec) {
  if (spec === '@devzoy/indian-pincode') return core;
  if (spec === '@devzoy/indian-pincode-geo') return geo;
  return createRequire(import.meta.url)(spec);
}

const failures = [];
let ran = 0;

for (const block of blocks) {
  // Expected outputs, in order, from `// =>` markers.
  const expected = [];
  for (const line of block.code.split('\n')) {
    const m = line.match(/\/\/\s*=>\s*(.+?)\s*$/);
    if (m) expected.push(m.groups ? m.groups[0] : m[1]);
  }
  // Rewrite ESM `import x from 'spec'` to require (blocks are CJS-executable).
  let code = block.code.replace(
    /import\s+(\w+)\s+from\s+['"]([^'"]+)['"];?/g,
    "const $1 = require('$2');"
  );

  const logged = [];
  const sandboxConsole = { log: (...a) => logged.push(a.map(String).join(' ')) };
  try {
    // eslint-disable-next-line no-new-func
    const fn = new Function('require', 'console', code);
    fn(fakeRequire, sandboxConsole);
  } catch (e) {
    failures.push(`${block.file}: block threw ${e.message}`);
    ran++;
    continue;
  }

  if (expected.length) {
    if (logged.length !== expected.length) {
      failures.push(`${block.file}: ${logged.length} log(s) but ${expected.length} expected`);
    } else {
      for (let i = 0; i < expected.length; i++) {
        if (logged[i] !== expected[i]) {
          failures.push(`${block.file}: log #${i + 1} -> ${JSON.stringify(logged[i])} != expected ${JSON.stringify(expected[i])}`);
        }
      }
    }
  }
  ran++;
}

if (failures.length) {
  console.error('README node examples FAILED:');
  for (const f of failures) console.error('  -', f);
  process.exit(1);
}
console.log(`README node examples OK (${ran} blocks)`);
