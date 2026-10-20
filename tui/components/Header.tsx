import React from 'react';

interface HeaderProps {
  searchQuery: string;
  scopeAll: boolean;
  currentCwd: string;
  totalCount: number;
  filteredCount: number;
}

export function Header({
  searchQuery,
  scopeAll,
  currentCwd,
  totalCount,
  filteredCount,
}: HeaderProps) {
  const folderName = currentCwd.split(/[\\/]/).filter(Boolean).pop() || currentCwd;

  return (
    <box
      flexDirection="column"
      borderStyle="round"
      borderColor="#06B6D4"
      padding={1}
      margin={0}
      width="100%"
    >
      {/* Top Banner */}
      <box flexDirection="row" justifyContent="space-between" width="100%">
        <box flexDirection="row" gap={1}>
          <text bold color="#06B6D4">
            ⚡ RESUME
          </text>
          <text dim color="#94A3B8">
            SameThread Unified Coding Agent Sessions
          </text>
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#64748B">Scope:</text>
          <text bold color={scopeAll ? '#F59E0B' : '#10B981'}>
            {scopeAll ? '🌐 All Projects' : `📁 ${folderName}`}
          </text>
          <text dim color="#64748B">
            (Tab to toggle)
          </text>
        </box>
      </box>

      {/* Search and Counts Row */}
      <box flexDirection="row" justifyContent="space-between" width="100%" marginTop={1}>
        <box flexDirection="row" gap={1}>
          <text bold color="#38BDF8">
            🔎 Filter:
          </text>
          {searchQuery ? (
            <box flexDirection="row">
              <text bold color="#FFFFFF">
                {searchQuery}
              </text>
              <text color="#06B6D4">█</text>
            </box>
          ) : (
            <text dim color="#475569">
              Type anywhere to search chats... (Esc to clear)
            </text>
          )}
        </box>
        <box flexDirection="row" gap={1}>
          <text color="#94A3B8">
            Showing <text bold color="#38BDF8">{filteredCount}</text> of <text bold color="#FFFFFF">{totalCount}</text> chats
          </text>
        </box>
      </box>
    </box>
  );
}
