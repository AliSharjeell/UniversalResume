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
      {/* GHUI-style ASCII Branding */}
      <box marginBottom={1}>
        <ascii-font text="UNIVERSAL RESUME" font="tiny" color="#38BDF8" />
      </box>

      {/* Scope Switcher */}
      <box flexDirection="column" marginBottom={1}>
        <text dim color="#64748B">
          Tab to switch scope:
        </text>
        <box flexDirection="row" justifyContent="space-between" width="100%">
          <box flexDirection="row" gap={2}>
            <text bold color={!scopeAll ? '#38BDF8' : '#64748B'}>
              {!scopeAll ? `[ In Folder: ${folderName} (${inFolderCount}) ]` : `  In Folder: ${folderName} (${inFolderCount})  `}
            </text>
            <text bold color={scopeAll ? '#38BDF8' : '#64748B'}>
              {scopeAll ? `[ Global (${globalCount}) ]` : `  Global (${globalCount})  `}
            </text>
          </box>
          <text color={isSyncing ? '#F59E0B' : '#64748B'}>
            {isSyncing ? 'Syncing...' : 'Synced'}
          </text>
        </box>
      </box>

      {/* Search Bar */}
      <box flexDirection="row">
        <text color="#94A3B8">Search: </text>
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
