import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const CORE_ENTRY = join(ROOT, 'packages', 'node-core', 'src', 'index.mjs');
const ESBUILD = join(ROOT, 'node_modules', '.bin', 'esbuild');

const NODE_BUILTINS = [
  'fs', 'path', 'url', 'os', 'crypto', 'zlib', 'http', 'https', 'net',
  'node:fs', 'node:path', 'node:url', 'node:os', 'node:zlib',
];

test('esbuild browser bundle of core builds with no Node built-ins', () => {
  const outfile = join(mkdtempSync(join(tmpdir(), 'ip-bundle-')), 'core.js');
  execFileSync(ESBUILD, [
    CORE_ENTRY, '--bundle', '--platform=browser', '--format=esm', `--outfile=${outfile}`,
  ]);
  const bundle = readFileSync(outfile, 'utf8');
  for (const b of NODE_BUILTINS) {
    assert.ok(!new RegExp(`require\\(["']${b}["']\\)`).test(bundle),
      `bundle should not require('${b}')`);
    assert.ok(!new RegExp(`from ["']${b}["']`).test(bundle),
      `bundle should not import from '${b}'`);
  }
  // sanity: the bundle actually contains the API
  assert.ok(bundle.includes('validate') && bundle.includes('getDetails'));
});

test('core imports and works inside an esbuild-bundled browser artifact', () => {
  // Bundle to CJS and require the artifact to prove it self-contains its data.
  const dir = mkdtempSync(join(tmpdir(), 'ip-bundle-cjs-'));
  const outfile = join(dir, 'core.cjs');
  execFileSync(ESBUILD, [
    CORE_ENTRY, '--bundle', '--platform=browser', '--format=cjs', `--outfile=${outfile}`,
  ]);
  const mod = require(outfile);
  assert.equal(mod.validate('110001'), true);
  assert.equal(mod.getState('560001'), 'KARNATAKA');
});
