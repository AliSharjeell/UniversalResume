export type AgentKey =
  | 'codex'
  | 'cc'
  | 'agy'
  | 'oc'
  | 'gemini'
  | 'qwen'
  | 'pi'
  | 'kimi'
  | 'mmx';

export interface AgentInfo {
  key: AgentKey;
  name: string;
  shortName: string;
  cliName: string;
  installed: boolean;
  writable: boolean;
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

export type ViewMode = 'intro' | 'list' | 'agent-picker';
