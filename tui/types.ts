export type AgentKey =
  | 'codex'
  | 'cc'
  | 'cursor'
  | 'agy'
  | 'grok'
  | 'deepseek'
  | 'hermes'
  | 'openclaw'
  | 'aider'
  | 'oc'
  | 'openhands'
  | 'qwen'
  | 'kimi'
  | 'mmx'
  | 'pi';

export interface AgentInfo {
  key: AgentKey;
  name: string;
  shortName: string;
  cliName: string;
  installed: boolean;
  writable: boolean;
  copyable: boolean;
  color: string;
  badgeBg: string;
  shortcut: string;
  description: string;
}

export interface ThreadCopy {
  tool: string;
  agentName: string;
  sid: string;
  owned: boolean;
  upto: number;
  behind: boolean;
  resumeCmd: string;
}

export interface TranscriptTurn {
  role: 'user' | 'assistant' | 'tool';
  author: string;
  text: string;
}

export interface ThreadItem {
  tid: string;
  title: string;
  baseTitle: string;
  tag: string;
  recentAgent: AgentKey;
  recentAgentName: string;
  recentAgentColor: string;
  cwd: string;
  folderName: string;
  updated: number;
  updatedAgo: string;
  turnCount: number;
  userTurns: number;
  assistantTurns: number;
  firstUserPrompt: string;
  lastUserPrompt: string;
  lastAssistantReply: string;
  copies: Record<string, ThreadCopy>;
  participants: string[];
}

export type ViewMode = 'list' | 'agent-picker';
