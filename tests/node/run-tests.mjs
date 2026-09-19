#!/usr/bin/env node
// Runs every *.test.mjs file in this directory via `node --test`, passing an
// explicit file list instead of a glob string. Node's test runner only
// resolves glob patterns natively on Node 22+, and a bare directory argument
// isn't recursively scanned — an explicit list works identically on every
// supported Node version and OS.
import { execFileSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const files = readdirSync(DIR)
  .filter((f) => f.endsWith('.test.mjs'))
  .sort()
  .map((f) => join(DIR, f));

if (files.length === 0) {
  console.error(`No *.test.mjs files found in ${DIR}`);
  process.exit(1);
}

try {
  execFileSync(process.execPath, ['--test', ...files], { stdio: 'inherit' });
} catch (err) {
  process.exit(err.status ?? 1);
}
