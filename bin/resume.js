#!/usr/bin/env bun
import path from 'node:path';
import fs from 'node:fs';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import { spawn, spawnSync } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const tuiEntry = path.resolve(__dirname, '..', 'tui', 'index.tsx');
const hopDir = process.env.HOP_HOME || path.join(os.homedir(), '.hop');
const pendingLaunchFile = path.join(hopDir, 'pending_launch.json');

// Remove any stale pending launch request
if (fs.existsSync(pendingLaunchFile)) {
  try {
    fs.unlinkSync(pendingLaunchFile);
  } catch {}
}

// 1. Run the interactive OpenTUI selector synchronously
const tuiResult = spawnSync('bun', ['run', tuiEntry, ...process.argv.slice(2)], {
  stdio: 'inherit',
  env: {
    ...process.env,
    RESUME_RUNNER: '1',
  },
});

// If TUI exited non-zero or was aborted, exit
if (tuiResult.status !== 0) {
  process.exit(tuiResult.status ?? 0);
}

// 2. Launch the selected agent in the restored interactive terminal
if (fs.existsSync(pendingLaunchFile)) {
  let launchSpec = null;
  try {
    launchSpec = JSON.parse(fs.readFileSync(pendingLaunchFile, 'utf8'));
    fs.unlinkSync(pendingLaunchFile);
  } catch (err) {
    console.error('Failed to parse launch target:', err);
    process.exit(1);
  }

  if (launchSpec && launchSpec.agentKey && launchSpec.tid) {
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const universalResumeDir = path.resolve(__dirname, '..');
    const srcDir = path.join(universalResumeDir, 'src');
    const targetCwd =
      launchSpec.cwd && path.isAbsolute(launchSpec.cwd) && fs.existsSync(launchSpec.cwd)
        ? launchSpec.cwd
        : process.cwd();

    const env = {
      ...process.env,
      PYTHONPATH: srcDir + (process.platform === 'win32' ? ';' : ':') + (process.env.PYTHONPATH || ''),
    };

    const agentProc = spawn(pythonCmd, ['-m', 'samethread', 'resume', launchSpec.agentKey, launchSpec.tid], {
      cwd: targetCwd,
      stdio: 'inherit',
      env,
    });

    agentProc.on('exit', (code) => {
      process.exit(code ?? 0);
    });

    agentProc.on('error', (err) => {
      console.error(`Failed to launch agent: ${err.message}`);
      process.exit(1);
    });
  }
}
