import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { execSync, spawn, spawnSync } from 'node:child_process';
import type { AgentInfo, AgentKey, ThreadCopy, ThreadItem } from './types.ts';

export const HOP_DIR = process.env.HOP_HOME || path.join(os.homedir(), '.hop');
export const THREADS_DIR = path.join(HOP_DIR, 'threads');
export const INDEX_FILE = path.join(HOP_DIR, 'index.json');

export const AGENT_REGISTRY: Record<AgentKey, {
  name: string;
  shortName: string;
  cliName: string;
  color: string;
  badgeBg: string;
  shortcut: string;
  writable: boolean;
  description: string;
}> = {
  codex: {
    name: 'Codex CLI',
    shortName: 'Codex',
    cliName: 'codex',
    color: '#10B981', // emerald green
    badgeBg: '#064E3B',
    shortcut: '1',
    writable: true,
    description: 'OpenAI rollout session store',
  },
  cc: {
    name: 'Claude Code',
    shortName: 'Claude',
    cliName: 'claude',
    color: '#F59E0B', // amber
    badgeBg: '#78350F',
    shortcut: '2',
    writable: true,
    description: 'Anthropic JSONL session store',
  },
  cursor: {
    name: 'Cursor CLI',
    shortName: 'Cursor',
    cliName: 'cursor-agent',
    color: '#38BDF8', // sky blue
    badgeBg: '#0369A1',
    shortcut: '3',
    writable: false,
    description: 'Cursor agent CLI sessions',
  },
  agy: {
    name: 'Antigravity (Agy)',
    shortName: 'Agy',
    cliName: 'agy',
    color: '#06B6D4', // cyan
    badgeBg: '#164E63',
    shortcut: '4',
    writable: false,
    description: 'Google DeepMind Antigravity CLI',
  },
  grok: {
    name: 'Grok Build',
    shortName: 'Grok',
    cliName: 'grok',
    color: '#E2E8F0', // silver white
    badgeBg: '#334155',
    shortcut: '5',
    writable: false,
    description: 'xAI Grok build and coding CLI',
  },
  deepseek: {
    name: 'DeepSeek Harness',
    shortName: 'DeepSeek',
    cliName: 'deepseek',
    color: '#6366F1', // indigo
    badgeBg: '#312E81',
    shortcut: '6',
    writable: false,
    description: 'DeepSeek Coder harness sessions',
  },
  hermes: {
    name: 'Hermes Agent',
    shortName: 'Hermes',
    cliName: 'hermes',
    color: '#EC4899', // pink
    badgeBg: '#831843',
    shortcut: '7',
    writable: false,
    description: 'Nous Research Hermes agent CLI',
  },
  openclaw: {
    name: 'OpenClaw',
    shortName: 'OpenClaw',
    cliName: 'openclaw',
    color: '#F97316', // orange
    badgeBg: '#7C2D12',
    shortcut: '8',
    writable: false,
    description: 'OpenClaw autonomous agent sessions',
  },
  aider: {
    name: 'Aider',
    shortName: 'Aider',
    cliName: 'aider',
    color: '#A855F7', // purple
    badgeBg: '#581C87',
    shortcut: '9',
    writable: false,
    description: 'Aider AI pair programmer CLI',
  },
  oc: {
    name: 'OpenCode',
    shortName: 'OpenCode',
    cliName: 'opencode',
    color: '#D946EF', // fuchsia / magenta
    badgeBg: '#701A75',
    shortcut: '10',
    writable: true,
    description: 'Anomaly OpenCode SQLite database',
  },
  openhands: {
    name: 'OpenHands',
    shortName: 'OpenHands',
    cliName: 'openhands',
    color: '#0284C7', // light blue
    badgeBg: '#075985',
    shortcut: '11',
    writable: false,
    description: 'All-Hands OpenHands agent sessions',
  },
  qwen: {
    name: 'Qwen Code',
    shortName: 'Qwen',
    cliName: 'qwen',
    color: '#EAB308', // gold yellow
    badgeBg: '#713F12',
    shortcut: '12',
    writable: true,
    description: 'Alibaba Qwen Code sessions',
  },
  kimi: {
    name: 'Kimi Code',
    shortName: 'Kimi',
    cliName: 'kimi',
    color: '#8B5CF6', // violet
    badgeBg: '#4C1D95',
    shortcut: '13',
    writable: true,
    description: 'Moonshot Kimi Code sessions',
  },
  mmx: {
    name: 'MiniMax Code',
    shortName: 'MiniMax',
    cliName: 'minimax',
    color: '#F43F5E', // rose / coral
    badgeBg: '#881337',
    shortcut: '14',
    writable: false,
    description: 'MiniMax SQLite session store',
  },
  pi: {
    name: 'Pi Agent',
    shortName: 'Pi',
    cliName: 'pi',
    color: '#14B8A6', // teal
    badgeBg: '#134E4A',
    shortcut: '15',
    writable: true,
    description: 'Inflection Pi agent entry tree',
  },
};

export function isCommandAvailable(cmd: string): boolean {
  try {
    if (process.platform === 'win32') {
      execSync(`where.exe ${cmd}`, { stdio: 'ignore' });
    } else {
      execSync(`which ${cmd}`, { stdio: 'ignore' });
    }
    return true;
  } catch {
    return false;
  }
}

export function detectAgents(): AgentInfo[] {
  const home = os.homedir();
  const checks: Record<AgentKey, boolean> = {
    codex: isCommandAvailable('codex') || fs.existsSync(path.join(home, '.codex')),
    cc: isCommandAvailable('claude') || fs.existsSync(path.join(home, '.claude')),
    cursor: isCommandAvailable('cursor-agent') || isCommandAvailable('cursor') || fs.existsSync(path.join(home, '.cursor')),
    agy: isCommandAvailable('agy') || fs.existsSync(path.join(home, '.gemini', 'antigravity-cli')) || fs.existsSync(path.join(home, 'AppData', 'Local', 'agy')),
    grok: isCommandAvailable('grok') || isCommandAvailable('grok-build') || fs.existsSync(path.join(home, '.grok')),
    deepseek: isCommandAvailable('deepseek') || isCommandAvailable('deepseek-harness') || fs.existsSync(path.join(home, '.deepseek')),
    hermes: isCommandAvailable('hermes') || isCommandAvailable('hermes-agent') || fs.existsSync(path.join(home, '.hermes')),
    openclaw: isCommandAvailable('openclaw') || isCommandAvailable('claw') || fs.existsSync(path.join(home, '.openclaw')),
    aider: isCommandAvailable('aider') || fs.existsSync(path.join(home, '.aider')),
    oc: isCommandAvailable('opencode') || fs.existsSync(path.join(home, '.local', 'share', 'opencode')),
    openhands: isCommandAvailable('openhands') || fs.existsSync(path.join(home, '.openhands')),
    qwen: isCommandAvailable('qwen') || fs.existsSync(path.join(home, '.qwen')),
    kimi: isCommandAvailable('kimi') || fs.existsSync(path.join(home, '.kimi-code')),
    mmx: isCommandAvailable('minimax') || isCommandAvailable('mcode') || fs.existsSync(path.join(home, '.minimax')),
    pi: isCommandAvailable('pi') || fs.existsSync(path.join(home, '.pi')),
  };

  const list = (Object.keys(AGENT_REGISTRY) as AgentKey[]).map((key) => {
    const meta = AGENT_REGISTRY[key];
    return {
      key,
      name: meta.name,
      shortName: meta.shortName,
      cliName: meta.cliName,
      installed: checks[key] ?? false,
      writable: meta.writable,
      color: meta.color,
      badgeBg: meta.badgeBg,
      shortcut: meta.shortcut,
      description: meta.description,
    };
  });

  // Sort installed agents first so users don't get overwhelmed and 1-9 shortcuts map to installed agents
  list.sort((a, b) => {
    if (a.installed === b.installed) return 0;
    return a.installed ? -1 : 1;
  });

  list.forEach((agent, idx) => {
    agent.shortcut = String(idx + 1);
  });

  return list;
}

export function formatAgo(ms: number): string {
  if (!ms) return 'never';
  const deltaSec = Math.max(0, Math.floor((Date.now() - ms) / 1000));
  if (deltaSec < 60) return 'just now';
  const deltaMin = Math.floor(deltaSec / 60);
  if (deltaMin < 60) return `${deltaMin}m ago`;
  const deltaHours = Math.floor(deltaMin / 60);
  if (deltaHours < 24) return `${deltaHours}h ago`;
  const deltaDays = Math.floor(deltaHours / 24);
  if (deltaDays < 30) return `${deltaDays}d ago`;
  const deltaMonths = Math.floor(deltaDays / 30);
  return `${deltaMonths}mo ago`;
}

function resolveAgentKey(toolOrKey: string): AgentKey {
  const lower = toolOrKey.toLowerCase();
  if (lower === 'codex') return 'codex';
  if (lower === 'cc' || lower === 'claude') return 'cc';
  if (lower === 'cursor' || lower === 'cursor-cli' || lower === 'cursor-agent') return 'cursor';
  if (lower === 'agy' || lower === 'antigravity') return 'agy';
  if (lower === 'grok' || lower === 'grok-build' || lower === 'grok-cli') return 'grok';
  if (lower === 'deepseek' || lower === 'deepseek-harness' || lower === 'deepseek-cli') return 'deepseek';
  if (lower === 'hermes' || lower === 'harmes' || lower === 'hermes-agent') return 'hermes';
  if (lower === 'openclaw' || lower === 'claw') return 'openclaw';
  if (lower === 'aider' || lower === 'aider-chat') return 'aider';
  if (lower === 'oc' || lower === 'opencode') return 'oc';
  if (lower === 'openhands' || lower === 'all-hands' || lower === 'opendevin') return 'openhands';
  if (lower === 'qwen' || lower === 'qwen-code') return 'qwen';
  if (lower === 'kimi' || lower === 'kimi-code') return 'kimi';
  if (lower === 'mmx' || lower === 'minimax' || lower === 'mcode') return 'mmx';
  if (lower === 'pi') return 'pi';
  return 'agy';
}

export function loadAllThreads(): ThreadItem[] {
  if (!fs.existsSync(THREADS_DIR)) {
    return [];
  }

  const files = fs.readdirSync(THREADS_DIR).filter((f) => f.endsWith('.json'));
  const threads: ThreadItem[] = [];

  for (const file of files) {
    try {
      const fullPath = path.join(THREADS_DIR, file);
      const raw = fs.readFileSync(fullPath, 'utf8');
      const data = JSON.parse(raw);

      const tid = data.tid || path.basename(file, '.json');
      const baseTitle = data.base_title || 'Untitled Session';
      const cwd = data.cwd || process.cwd();
      const updated = Number(data.updated) || 0;
      const elements: any[] = Array.isArray(data.elements) ? data.elements : [];

      // Determine recent agent
      let recentAgentKey: AgentKey = 'agy';
      if (typeof data.head === 'string' && data.head.includes(':')) {
        recentAgentKey = resolveAgentKey(data.head.split(':')[0]);
      } else if (typeof data.origin === 'string') {
        recentAgentKey = resolveAgentKey(data.origin.split(':')[0]);
      }

      // Collect participants
      const participantSet = new Set<string>();
      for (const el of elements) {
        if (el?.author) {
          const key = resolveAgentKey(el.author);
          participantSet.add(AGENT_REGISTRY[key]?.shortName || el.author);
        }
      }
      if (participantSet.size === 0) {
        participantSet.add(AGENT_REGISTRY[recentAgentKey]?.shortName || 'Agy');
      }

      const tag = Array.from(participantSet).join('+');
      const title = `${baseTitle} (${tag})`;

      // Copies
      const copies: Record<string, ThreadCopy> = {};
      if (data.copies && typeof data.copies === 'object') {
        for (const [key, cp] of Object.entries<any>(data.copies)) {
          const tool = key.split(':')[0];
          const sid = key.split(':')[1] || '';
          const agentKey = resolveAgentKey(tool);
          const meta = AGENT_REGISTRY[agentKey];
          const upto = Number(cp.upto) || 0;
          const behind = upto < elements.length;

          let resumeCmd = `${meta?.cliName || tool} resume ${sid}`;
          if (agentKey === 'cc') resumeCmd = `claude --resume ${sid}`;
          if (agentKey === 'agy') resumeCmd = `agy --conversation ${sid}`;
          if (agentKey === 'cursor') resumeCmd = `cursor-agent resume ${sid}`;
          if (agentKey === 'grok') resumeCmd = `grok --resume ${sid}`;
          if (agentKey === 'deepseek') resumeCmd = `deepseek --resume ${sid}`;
          if (agentKey === 'hermes') resumeCmd = `hermes --resume ${sid}`;
          if (agentKey === 'openclaw') resumeCmd = `openclaw --resume ${sid}`;
          if (agentKey === 'aider') resumeCmd = `aider --restore-chat-history`;
          if (agentKey === 'openhands') resumeCmd = `openhands --resume ${sid}`;

          copies[agentKey] = {
            tool,
            agentName: meta?.shortName || tool,
            sid,
            owned: Boolean(cp.owned),
            upto,
            behind,
            resumeCmd,
          };
        }
      }

      // First user prompt and last user prompt
      let firstUserPrompt = '';
      let lastUserPrompt = '';
      let lastAssistantReply = '';
      let userTurns = 0;
      let assistantTurns = 0;

      for (const el of elements) {
        if (el?.role === 'user' && typeof el.text === 'string' && el.text.trim()) {
          userTurns++;
          if (!firstUserPrompt) firstUserPrompt = el.text.trim();
          lastUserPrompt = el.text.trim();
        } else if (el?.role === 'assistant' && typeof el.text === 'string' && el.text.trim()) {
          assistantTurns++;
          lastAssistantReply = el.text.trim();
        }
      }

      let folderName = path.basename(cwd) || cwd;
      if (
        !cwd ||
        cwd === '~' ||
        cwd.toLowerCase() === os.homedir().toLowerCase() ||
        cwd.toLowerCase() === path.resolve(os.homedir()).toLowerCase()
      ) {
        folderName = '~';
      }
      const recentAgentMeta = AGENT_REGISTRY[recentAgentKey] || AGENT_REGISTRY.agy;

      threads.push({
        tid,
        title,
        baseTitle,
        tag,
        recentAgent: recentAgentKey,
        recentAgentName: recentAgentMeta.shortName,
        recentAgentColor: recentAgentMeta.color,
        cwd,
        folderName,
        updated,
        updatedAgo: formatAgo(updated),
        turnCount: elements.length,
        userTurns,
        assistantTurns,
        firstUserPrompt: firstUserPrompt.slice(0, 300),
        lastUserPrompt: lastUserPrompt.slice(0, 300),
        lastAssistantReply: lastAssistantReply.slice(0, 300),
        copies,
        participants: Array.from(participantSet),
      });
    } catch {
      // Ignore unparseable files
    }
  }

  // Sort newest first
  threads.sort((a, b) => b.updated - a.updated);
  return threads;
}

export function filterThreads(
  threads: ThreadItem[],
  query: string,
  scopeAll: boolean,
  currentCwd: string
): ThreadItem[] {
  let list = threads;

  if (!scopeAll && currentCwd) {
    const normCwd = path.resolve(currentCwd).toLowerCase();
    list = list.filter((t) => path.resolve(t.cwd).toLowerCase() === normCwd);
  }

  if (!query || !query.trim()) {
    return list;
  }

  const q = query.trim().toLowerCase();
  return list.filter((t) => {
    return (
      t.title.toLowerCase().includes(q) ||
      t.baseTitle.toLowerCase().includes(q) ||
      t.recentAgentName.toLowerCase().includes(q) ||
      t.folderName.toLowerCase().includes(q) ||
      t.cwd.toLowerCase().includes(q) ||
      t.firstUserPrompt.toLowerCase().includes(q) ||
      t.lastUserPrompt.toLowerCase().includes(q)
    );
  });
}

export async function runSync(): Promise<{ success: boolean; message: string }> {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const universalResumeDir = path.resolve(__dirname, '..');

  return new Promise((resolve) => {
    const child = spawn(
      pythonCmd,
      [
        '-c',
        `import sys; sys.path.insert(0, r'${path.join(universalResumeDir, 'src')}'); from samethread.cli import main; sys.argv=['hop', 'sync', '-q']; main()`
      ],
      {
        cwd: universalResumeDir,
        stdio: 'ignore',
      }
    );

    child.on('exit', (code) => {
      resolve({
        success: code === 0,
        message: code === 0 ? '✓ Synced coding agent sessions' : 'Sync completed with warnings',
      });
    });

    child.on('error', (err) => {
      resolve({
        success: false,
        message: `Sync error: ${err.message}`,
      });
    });
  });
}

export function runSyncSync(): boolean {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const universalResumeDir = path.resolve(__dirname, '..');
  try {
    const res = spawnSync(
      pythonCmd,
      [
        '-c',
        `import sys; sys.path.insert(0, r'${path.join(universalResumeDir, 'src')}'); from samethread.cli import main; sys.argv=['hop', 'sync', '-q']; main()`
      ],
      {
        cwd: universalResumeDir,
        stdio: 'ignore',
      }
    );
    return res.status === 0;
  } catch {
    return false;
  }
}

