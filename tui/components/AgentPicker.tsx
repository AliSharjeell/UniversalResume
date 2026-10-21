import React from 'react';
import { TextAttributes } from '@opentui/core';
import type { AgentInfo, AgentKey, ThreadItem } from '../types.ts';

interface AgentPickerProps {
  thread: ThreadItem;
  agents: AgentInfo[];
  selectedIndex: number;
  onSelect?: (agentKey: AgentKey) => void;
}

export function AgentPicker({
  thread,
  agents,
  selectedIndex,
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

      <box flexDirection="column" marginBottom={1}>
        {agents.map((agent, idx) => {
          const isSelected = idx === selectedIndex;
          const isRecent = agent.key === thread.recentAgent;
          const hasCopy = Boolean(thread.copies[agent.key]);
          const mode = hasCopy
            ? 'native copy'
            : agent.writable
            ? 'native mirror'
            : 'seeded handoff';
          const recentTag = isRecent ? ' (recent agent)' : '';

          const prefix = isSelected ? '> ' : '  ';
          const num = `${agent.shortcut}.`.padEnd(4);
          const name = agent.name.padEnd(24);
          const modeStr = mode.padEnd(20);
          const line = `${prefix}${num}${name}${modeStr}${recentTag}`;

          return (
            <box
              key={agent.key}
              width="100%"
              backgroundColor={isSelected ? '#262626' : undefined}
              onMouseDown={() => onSelect && onSelect(agent.key)}
            >
              <text
                attributes={isSelected ? TextAttributes.BOLD : TextAttributes.NONE}
                fg={isSelected ? '#FFFFFF' : '#A3A3A3'}
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
