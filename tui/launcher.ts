import { spawn } from 'node:child_process';
import path from 'node:path';
import type { AgentKey, ThreadItem } from './types.ts';

export function launchResume(thread: ThreadItem, agentKey: AgentKey, onComplete?: () => void) {
  // Find python executable
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const universalResumeDir = path.resolve(__dirname, '..');

  // We invoke the Python samethread module with resume command
  const args = [
    '-c',
    `import sys; sys.path.insert(0, r'${path.join(universalResumeDir, 'src')}'); from samethread.cli import main; sys.argv=['hop', 'resume', '${agentKey}', '${thread.tid}']; main()`
  ];

  const targetCwd = thread.cwd && path.isAbsolute(thread.cwd) ? thread.cwd : process.cwd();

  const child = spawn(pythonCmd, args, {
    cwd: targetCwd,
    stdio: 'inherit',
    shell: true,
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
