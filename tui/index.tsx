import React from 'react';
import { createCliRenderer } from '@opentui/core';
import { createRoot } from '@opentui/react';
import { App } from './App.tsx';
import { launchResume } from './launcher.ts';
import type { AgentKey, ThreadItem } from './types.ts';

async function main() {
  const args = process.argv.slice(2);
  let initialQuery = '';
  let cwd = process.cwd();

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--cwd' && args[i + 1]) {
      cwd = args[++i];
    } else if (!arg.startsWith('-')) {
      initialQuery = arg;
    }
  }

  // Create OpenTUI CLI renderer
  const renderer = await createCliRenderer({
    exitOnCtrlC: false,
  });

  const root = createRoot(renderer);

  const handleLaunch = async (thread: ThreadItem, agentKey: AgentKey) => {
    try {
      renderer.destroy();
      await renderer.closed;
    } catch {
      // Ignore destroy errors
    }
    launchResume(thread, agentKey);
  };

  const handleExit = async () => {
    try {
      renderer.destroy();
      await renderer.closed;
    } catch {
      // Ignore destroy errors
    }
    process.exit(0);
  };

  process.on('SIGINT', handleExit);
  process.on('SIGTERM', handleExit);

  root.render(
    <App
      currentCwd={cwd}
      initialQuery={initialQuery}
      onLaunch={handleLaunch}
      onExit={handleExit}
    />
  );
}

main().catch((err) => {
  console.error('Fatal TUI error:', err);
  process.exit(1);
});
