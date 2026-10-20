import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn } from 'node:child_process';
import type { AgentKey, ThreadItem } from './types.ts';

const HOP_DIR = process.env.HOP_HOME || path.join(os.homedir(), '.hop');
const PENDING_LAUNCH_FILE = path.join(HOP_DIR, 'pending_launch.json');

export function launchResume(thread: ThreadItem, agentKey: AgentKey, onComplete?: () => void) {
  const targetCwd = thread.cwd && path.isAbsolute(thread.cwd) ? thread.cwd : process.cwd();

  // Write pending launch request for the parent resume runner
  try {
    if (!fs.existsSync(HOP_DIR)) {
      fs.mkdirSync(HOP_DIR, { recursive: true });
    }
    fs.writeFileSync(
      PENDING_LAUNCH_FILE,
      JSON.stringify({
        tid: thread.tid,
        agentKey,
        cwd: targetCwd,
      }),
      'utf8'
    );
  } catch (err) {
    console.error('Failed to save launch intent:', err);
  }

  // If invoked via resume runner (bin/resume.js), cleanly exit now so the parent process
  // restores the terminal to interactive TTY and launches the agent directly.
  if (process.env.RESUME_RUNNER === '1') {
    if (onComplete) onComplete();
    process.exit(0);
  }

  // Standalone fallback if tui/index.tsx was invoked directly without runner
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const universalResumeDir = path.resolve(__dirname, '..');
  const srcDir = path.join(universalResumeDir, 'src');

  const env = {
    ...process.env,
    PYTHONPATH: srcDir + (process.platform === 'win32' ? ';' : ':') + (process.env.PYTHONPATH || ''),
  };

  if (process.stdin.resume) {
    process.stdin.resume();
  }

  const child = spawn(pythonCmd, ['-m', 'samethread.cli', 'resume', agentKey, thread.tid], {
    cwd: targetCwd,
    stdio: 'inherit',
    env,
  });

  child.on('exit', (code) => {
    if (onComplete) onComplete();
    process.exit(code ?? 0);
  });

  child.on('error', (err) => {
    console.error(`Failed to launch agent: ${err.message}`);
    if (onComplete) onComplete();
    process.exit(1);
  });
}
