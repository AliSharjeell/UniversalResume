import React from 'react';
import type { ThreadItem } from '../types.ts';

interface ChatListProps {
  threads: ThreadItem[];
  selectedIndex: number;
  maxVisible?: number;
  scopeAll: boolean;
}

export function ChatList({
  threads,
  selectedIndex,
  maxVisible = 15,
  scopeAll,
}: ChatListProps) {
  if (threads.length === 0) {
    return (
      <box
        flexDirection="column"
        borderStyle="round"
        borderColor="#334155"
        padding={1}
        flexGrow={1}
        height="100%"
      >
        <box marginBottom={1}>
          <text bold color="#94A3B8">
            CHATS LIST
          </text>
        </box>
        <box flexDirection="column" padding={2} alignItems="center" justifyContent="center">
          <text color="#E2E8F0" bold>
            No matching conversations found
          </text>
          <text dim color="#64748B" marginTop={1}>
            Press Tab to view all projects, or Backspace to clear filter
          </text>
        </box>
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

  return (
    <box
      flexDirection="column"
      borderStyle="round"
      borderColor="#06B6D4"
      padding={1}
      flexGrow={1}
      height="100%"
    >
      {/* Title bar */}
      <box flexDirection="row" justifyContent="space-between" marginBottom={1}>
        <text bold color="#38BDF8">
          RECENT CONVERSATIONS
        </text>
        <text dim color="#64748B">
          {safeSelected + 1} / {threads.length}
        </text>
      </box>

      {/* Items list */}
      <box flexDirection="column" gap={0} flexGrow={1}>
        {visibleThreads.map((thread, idx) => {
          const actualIndex = startIdx + idx;
          const isSelected = actualIndex === safeSelected;

          return (
            <box
              key={thread.tid}
              flexDirection="row"
              justifyContent="space-between"
              paddingLeft={1}
              paddingRight={1}
              backgroundColor={isSelected ? '#0F2942' : undefined}
            >
              {/* Left side: pointer, agent badge, title */}
              <box flexDirection="row" gap={1} flexGrow={1} flexShrink={1}>
                {isSelected ? (
                  <text bold color="#38BDF8">
                    ❯
                  </text>
                ) : (
                  <text color="#334155"> </text>
                )}

                {/* Agent badge */}
                <text bold color={thread.recentAgentColor}>
                  [{thread.recentAgentName}]
                </text>

                {/* Title */}
                <text
                  bold={isSelected}
                  color={isSelected ? '#FFFFFF' : '#CBD5E1'}
                >
                  {thread.baseTitle}
                </text>
              </box>

              {/* Right side: folder & timestamp */}
              <box flexDirection="row" gap={1} flexShrink={0} paddingLeft={2}>
                {scopeAll ? (
                  <text dim color="#64748B">
                    {thread.folderName}
                  </text>
                ) : null}
                <text color={isSelected ? '#38BDF8' : '#64748B'}>
                  {thread.updatedAgo}
                </text>
              </box>
            </box>
          );
        })}
      </box>
    </box>
  );
}
