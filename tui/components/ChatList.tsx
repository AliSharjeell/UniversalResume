import React from 'react';
import type { ThreadItem } from '../types.ts';

interface ChatListProps {
  threads: ThreadItem[];
  selectedIndex: number;
  maxVisible?: number;
  scopeAll: boolean;
  termWidth?: number;
}

export function ChatList({
  threads,
  selectedIndex,
  maxVisible = 15,
  scopeAll,
  termWidth = 80,
}: ChatListProps) {
  if (threads.length === 0) {
    return (
      <box flexDirection="column" padding={2} alignItems="center" justifyContent="center" flexGrow={1}>
        <text color="#E2E8F0" bold>
          No conversations found
        </text>
        <text dim color="#64748B" marginTop={1}>
          Press Tab to switch scope, or Backspace to clear search
        </text>
      </box>
    );
  }

  // Calculate scrolling window
  const safeSelected = Math.max(0, Math.min(selectedIndex, threads.length - 1));
  let startIdx = 0;
  if (threads.length > maxVisible) {
    const half = Math.floor(maxVisible / 2);
    if (safeSelected <= half) {
      startIdx = 0;
    } else if (safeSelected >= threads.length - half) {
      startIdx = threads.length - maxVisible;
    } else {
      startIdx = safeSelected - half;
    }
  }
  const visibleThreads = threads.slice(startIdx, startIdx + maxVisible);

  // Column calculations
  const maxLineW = Math.max(50, termWidth - 4);
  const agentColW = 10;
  const timeColW = 10;
  const folderColW = scopeAll ? 16 : 0;
  const titleColW = Math.max(20, maxLineW - 2 - agentColW - timeColW - folderColW);

  return (
    <box flexDirection="column" flexGrow={1}>
      {visibleThreads.map((thread, idx) => {
        const actualIndex = startIdx + idx;
        const isSelected = actualIndex === safeSelected;

        const prefix = isSelected ? '> ' : '  ';

        // Truncate title
        let title = thread.baseTitle;
        if (title.length > titleColW - 1) {
          title = title.slice(0, titleColW - 2) + '…';
        }
        const titleStr = title.padEnd(titleColW);

        const agentStr = thread.recentAgentName.padEnd(agentColW);
        const folderStr = scopeAll
          ? (thread.folderName.length > folderColW - 1
              ? thread.folderName.slice(0, folderColW - 2) + '…'
              : thread.folderName
            ).padEnd(folderColW)
          : '';
        const timeStr = thread.updatedAgo.padStart(timeColW);

        let line = `${prefix}${titleStr}${agentStr}${folderStr}${timeStr}`;
        if (line.length > maxLineW) {
          line = line.slice(0, maxLineW);
        }

        return (
          <box
            key={thread.tid}
            width="100%"
            backgroundColor={isSelected ? '#1E3A5F' : undefined}
          >
            <text
              bold={isSelected}
              color={isSelected ? '#FACC15' : '#CBD5E1'}
            >
              {line}
            </text>
          </box>
        );
      })}
    </box>
  );
}
