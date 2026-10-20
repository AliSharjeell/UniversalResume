#!/usr/bin/env bun
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const tuiEntry = path.resolve(__dirname, '..', 'tui', 'index.tsx');

const child = spawn('bun', ['run', tuiEntry, ...process.argv.slice(2)], {
  stdio: 'inherit',
  shell: true,
});

child.on('exit', (code) => {
  process.exit(code ?? 0);
});
