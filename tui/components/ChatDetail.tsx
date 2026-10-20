import React from 'react';
import type { AgentInfo, ThreadItem } from '../types.ts';

interface ChatDetailProps {
  thread: ThreadItem | null;
  agents: AgentInfo[];
}

export function ChatDetail({ thread, agents }: ChatDetailProps) {
  if (!thread) {
    return (
      <box
        flexDirection="column"
        borderStyle="round"
        borderColor="#334155"
        padding={1}
        width={48}
        height="100%"
      >
        <text bold color="#64748B">
          DETAILS & PREVIEW
        </text>
        <box marginTop={2} justifyContent="center" alignItems="center">
          <text dim color="#475569">
            Select a conversation on the left
          </text>
        </box>
      </box>
    );
  }

  // Active copies
  const activeCopies = Object.values(thread.copies);

  return (
    <box
      flexDirection="column"
      borderStyle="round"
      borderColor="#475569"
      padding={1}
      width={48}
      height="100%"
      gap={1}
    >
      {/* Title */}
      <box flexDirection="column">
        <text bold color="#38BDF8">
          DETAILS & PREVIEW
        </text>
        <text bold color="#FFFFFF">
          {thread.title}
        </text>
      </box>

      {/* Meta Information */}
      <box flexDirection="column" gap={0}>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">Recent Agent:</text>
          <text bold color={thread.recentAgentColor}>
            {thread.recentAgentName}
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">Directory:</text>
          <text color="#CBD5E1">
            {thread.cwd}
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">Last Active:</text>
          <text color="#F59E0B">
            {thread.updatedAgo}
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">Turns:</text>
          <text color="#CBD5E1">
            {thread.turnCount} turns ({thread.userTurns} user · {thread.assistantTurns} assistant)
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">History with:</text>
          <text color="#A78BFA">
            {thread.participants.join(', ')}
          </text>
        </box>
      </box>

      {/* Copies status */}
      <box flexDirection="column" marginTop={1}>
        <text bold color="#94A3B8">
          AGENT MIRRORS ({activeCopies.length})
        </text>
        {activeCopies.length === 0 ? (
          <text dim color="#64748B">
            No mirrors created yet
          </text>
        ) : (
          activeCopies.map((cp) => (
            <box key={cp.tool} flexDirection="row" justifyContent="space-between">
              <text color="#CBD5E1">
                {cp.agentName}:
              </text>
              <text color={cp.owned ? '#10B981' : '#06B6D4'}>
                {cp.owned ? 'Mirror' : 'Original'}{cp.behind ? ' (behind)' : ''}
              </text>
            </box>
          ))
        )}
      </box>

      {/* Transcript Preview */}
      <box
        flexDirection="column"
        borderStyle="single"
        borderColor="#334155"
        padding={1}
        marginTop={1}
        flexGrow={1}
      >
        <text bold color="#E2E8F0" marginBottom={1}>
          TRANSCRIPT PREVIEW
        </text>
        {thread.firstUserPrompt ? (
          <box flexDirection="column" gap={1}>
            <text bold color="#F59E0B">
              Initial Goal:
            </text>
            <text color="#94A3B8">
              "{thread.firstUserPrompt.slice(0, 150)}{thread.firstUserPrompt.length > 150 ? '...' : ''}"
            </text>
            {thread.lastAssistantReply ? (
              <box flexDirection="column">
                <text bold color="#10B981" marginTop={1}>
                  Last Assistant Reply:
                </text>
                <text color="#94A3B8">
                  "{thread.lastAssistantReply.slice(0, 150)}{thread.lastAssistantReply.length > 150 ? '...' : ''}"
                </text>
              </box>
            ) : null}
          </box>
        ) : (
          <text dim color="#64748B">
            No user messages recorded yet
          </text>
        )}
      </box>
    </box>
  );
}
