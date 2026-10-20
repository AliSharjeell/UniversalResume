import React from 'react';
import type { AgentInfo, ThreadItem } from '../types.ts';

interface AgentPickerProps {
  thread: ThreadItem;
  agents: AgentInfo[];
  selectedIndex: number;
}

export function AgentPicker({
  thread,
  agents,
  selectedIndex,
}: AgentPickerProps) {
  return (
    <box
      flexDirection="column"
      borderStyle="round"
      borderColor="#10B981"
      padding={1}
      width="100%"
      height="100%"
      gap={1}
    >
      {/* Header */}
      <box flexDirection="column" borderStyle="single" borderColor="#047857" padding={1}>
        <box flexDirection="row" justifyContent="space-between">
          <text bold color="#10B981">
            🚀 RESUME WITH AGENT
          </text>
          <text dim color="#94A3B8">
            [Esc] Back to chat list
          </text>
        </box>
        <box flexDirection="row" gap={1} marginTop={1}>
          <text color="#CBD5E1">Target Chat:</text>
          <text bold color="#FFFFFF">
            {thread.title}
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">Directory:</text>
          <text color="#38BDF8">
            {thread.cwd}
          </text>
        </box>
      </box>

      {/* Instruction */}
      <box marginTop={1}>
        <text bold color="#F59E0B">
          Choose which coding agent to open this conversation in (Press [1-9] or [↑/↓] + Enter):
        </text>
      </box>

      {/* Agents List */}
      <box flexDirection="column" gap={0} flexGrow={1} marginTop={1}>
        {agents.map((agent, idx) => {
          const isSelected = idx === selectedIndex;
          const isRecent = agent.key === thread.recentAgent;
          const hasCopy = Boolean(thread.copies[agent.key]);

          let statusBadge = agent.installed ? 'Installed' : 'Not found';
          let modeBadge = hasCopy
            ? 'Native copy ready'
            : agent.writable
            ? 'Native mirror'
            : 'Seed handoff';

          return (
            <box
              key={agent.key}
              flexDirection="row"
              justifyContent="space-between"
              paddingLeft={1}
              paddingRight={1}
              backgroundColor={isSelected ? '#064E3B' : undefined}
            >
              {/* Left side: pointer, number, name */}
              <box flexDirection="row" gap={1} alignItems="center">
                <text bold color="#10B981">
                  {isSelected ? '❯' : ' '}
                </text>
                <text bold color="#38BDF8">
                  [{agent.shortcut}]
                </text>
                <text bold color={agent.color}>
                  {agent.name}
                </text>
                <text dim color="#64748B">
                  ({agent.cliName})
                </text>
                {isRecent ? (
                  <text bold color="#F59E0B">
                    ★ Recent
                  </text>
                ) : null}
              </box>

              {/* Right side: installed and resume mode */}
              <box flexDirection="row" gap={2}>
                <text color={hasCopy ? '#10B981' : '#38BDF8'}>
                  [{modeBadge}]
                </text>
                <text color={agent.installed ? '#10B981' : '#64748B'}>
                  {agent.installed ? '● ready' : '○ missing'}
                </text>
              </box>
            </box>
          );
        })}
      </box>

      {/* Bottom Hint */}
      <box borderStyle="single" borderColor="#334155" padding={1} flexDirection="row" justifyContent="space-between">
        <text color="#94A3B8">
          Tip: Hop writes full history into native session stores or seeds via handoff transcript.
        </text>
        <text bold color="#10B981">
          [Enter] Launch Selected Agent
        </text>
      </box>
    </box>
  );
}
