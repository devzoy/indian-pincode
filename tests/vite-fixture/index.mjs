// Minimal entry that a Vite build bundles for the browser, proving the core
// package works in a bundler with no Node built-ins.
import pincode from '@devzoy/indian-pincode';

export function check() {
  if (pincode.validate('110001') !== true) throw new Error('validate failed');
  if (pincode.getState('560001') !== 'KARNATAKA') throw new Error('getState failed');
  return pincode.DATA_VERSION;
}

// Reference it so tree-shaking keeps the code.
globalThis.__ip_check = check;
