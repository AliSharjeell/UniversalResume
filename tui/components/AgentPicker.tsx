import React from 'react';
import { TextAttributes } from '@opentui/core';
import type { AgentInfo, AgentKey, ThreadItem } from '../types.ts';

interface AgentPickerProps {
  thread: ThreadItem;
  agents: AgentInfo[];
  selectedIndex: number;
  errorMessage?: string;
  onSelect?: (agentKey: AgentKey) => void;
}

export function AgentPicker({
  thread,
  agents,
  selectedIndex,
  errorMessage,
  onSelect,
}: AgentPickerProps) {
  return (
    <box flexDirection="column" flexGrow={1}>
      <text attributes={TextAttributes.BOLD} fg="#FFFFFF" marginBottom={1}>
        {`Resume: ${thread.baseTitle}`}
      </text>
      <text attributes={TextAttributes.DIM} fg="#737373" marginBottom={1}>
        {`Directory: ${thread.cwd}`}
      </text>
      <text attributes={TextAttributes.BOLD} fg="#FFFFFF" marginBottom={1}>
        Select agent to resume with (press 1-9, ↑/↓, or Enter):
      </text>

      {errorMessage && (
        <text attributes={TextAttributes.BOLD} fg="#F87171" marginBottom={1}>
          {`  ⚠  ${errorMessage}`}
        </text>
      )}

      <box flexDirection="column" marginBottom={1}>
        {agents.map((agent, idx) => {
          const isSelected = idx === selectedIndex;
          const isRecent = agent.key === thread.recentAgent;
          // A copy already in this agent is resumed as it stands; otherwise hop writes the chat
          // into the agent's own store first. Only agents that cannot be written get a handoff.
          const hasCopy = Boolean(thread.copies?.[agent.key]);
          const mode = hasCopy || agent.copyable ? 'native copy' : 'seeded handoff';
          const installedStr = agent.installed ? 'installed' : 'not installed';
          const recentTag = isRecent ? ' (recent agent)' : '';

          const prefix = isSelected ? '> ' : '  ';
          const num = `${agent.shortcut}.`.padEnd(4);
          const name = agent.name.padEnd(22);
          const modeStr = mode.padEnd(16);
          const statusStr = installedStr.padEnd(16);
          const line = `${prefix}${num}${name}${modeStr}${statusStr}${recentTag}`;

          const textColor = isSelected
            ? '#FFFFFF'
            : agent.installed
            ? '#E5E5E5'
            : '#525252';

          return (
            <box
              key={agent.key}
              width="100%"
              backgroundColor={isSelected ? '#262626' : undefined}
              onMouseDown={() => onSelect && onSelect(agent.key)}
            >
              <text
                attributes={isSelected ? TextAttributes.BOLD : TextAttributes.NONE}
                fg={textColor}
              >
                {line}
              </text>
            </box>
          );
        })}
      </box>

      <text attributes={TextAttributes.DIM} fg="#737373">
        [Enter] Launch   [1-9] Quick Pick   [Esc] Back to list
      </text>
    </box>
  );
}
