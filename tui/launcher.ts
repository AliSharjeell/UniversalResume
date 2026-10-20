import { spawn } from 'node:child_process';
import path from 'node:path';
import type { AgentKey, ThreadItem } from './types.ts';

export function launchResume(thread: ThreadItem, agentKey: AgentKey, onComplete?: () => void) {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const universalResumeDir = path.resolve(__dirname, '..');
  const srcDir = path.join(universalResumeDir, 'src');

  const targetCwd = thread.cwd && path.isAbsolute(thread.cwd) ? thread.cwd : process.cwd();

  const env = {
    ...process.env,
    PYTHONPATH: srcDir + (process.platform === 'win32' ? ';' : ':') + (process.env.PYTHONPATH || ''),
  };

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
