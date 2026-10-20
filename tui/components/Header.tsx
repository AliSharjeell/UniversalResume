import React from 'react';

interface HeaderProps {
  searchQuery: string;
  scopeAll: boolean;
  inFolderCount: number;
  globalCount: number;
  isSyncing: boolean;
  folderName: string;
}

export function Header({
  searchQuery,
  scopeAll,
  inFolderCount,
  globalCount,
  isSyncing,
  folderName,
}: HeaderProps) {
  return (
    <box flexDirection="column" marginBottom={1}>
      {/* Tab bar */}
      <box flexDirection="row" justifyContent="space-between" marginBottom={1}>
        <box flexDirection="row" gap={2}>
          <text bold color={!scopeAll ? '#38BDF8' : '#64748B'}>
            {!scopeAll ? `[ In Folder: ${folderName} (${inFolderCount}) ]` : `  In Folder: ${folderName} (${inFolderCount})  `}
          </text>
          <text bold color={scopeAll ? '#38BDF8' : '#64748B'}>
            {scopeAll ? `[ Global (${globalCount}) ]` : `  Global (${globalCount})  `}
          </text>
          <text dim color="#475569">
            (Tab to switch)
          </text>
        </box>
        <text color={isSyncing ? '#F59E0B' : '#64748B'}>
          {isSyncing ? 'Syncing...' : 'Synced'}
        </text>
      </box>

      {/* Filter bar */}
      <box flexDirection="row">
        <text color="#94A3B8">Filter: </text>
        {searchQuery ? (
          <text bold color="#FFFFFF">
            {searchQuery}█
          </text>
        ) : (
          <text dim color="#475569">
            type to search... (Esc to clear)
          </text>
        )}
      </box>
    </box>
  );
}
