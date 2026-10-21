import React from 'react';
import { TextAttributes } from '@opentui/core';

interface HeaderProps {
  searchQuery: string;
  scopeAll: boolean;
  inFolderCount: number;
  globalCount: number;
  isSyncing: boolean;
  folderName: string;
  onToggleScope?: () => void;
  onTriggerSync?: () => void;
}

export function Header({
  searchQuery,
  scopeAll,
  inFolderCount,
  globalCount,
  isSyncing,
  folderName,
  onToggleScope,
  onTriggerSync,
}: HeaderProps) {
  return (
    <box flexDirection="column" marginBottom={1}>
      {/* Monochrome ASCII Branding */}
      <box marginBottom={1}>
        <ascii-font text="UNIVERSAL RESUME" font="tiny" color="#FFFFFF" />
      </box>

      {/* Scope Switcher */}
      <box flexDirection="column" marginBottom={1}>
        <text attributes={TextAttributes.DIM} fg="#737373">
          Tab to switch scope:
        </text>
        <box flexDirection="row" justifyContent="space-between" width="100%">
          <box flexDirection="row" gap={2} onMouseDown={() => onToggleScope && onToggleScope()}>
            <text attributes={!scopeAll ? TextAttributes.BOLD : TextAttributes.NONE} fg={!scopeAll ? '#FFFFFF' : '#737373'}>
              {!scopeAll ? `[ In Folder: ${folderName} (${inFolderCount}) ]` : `  In Folder: ${folderName} (${inFolderCount})  `}
            </text>
            <text attributes={scopeAll ? TextAttributes.BOLD : TextAttributes.NONE} fg={scopeAll ? '#FFFFFF' : '#737373'}>
              {scopeAll ? `[ Global (${globalCount}) ]` : `  Global (${globalCount})  `}
            </text>
          </box>
          <box onMouseDown={() => onTriggerSync && onTriggerSync()}>
            <text fg={isSyncing ? '#FFFFFF' : '#737373'}>
              {isSyncing ? 'Syncing...' : 'Synced'}
            </text>
          </box>
        </box>
      </box>

      {/* Search Bar */}
      <box flexDirection="row">
        <text fg="#A3A3A3">Search: </text>
        {searchQuery ? (
          <text attributes={TextAttributes.BOLD} fg="#FFFFFF">
            {searchQuery}█
          </text>
        ) : (
          <text attributes={TextAttributes.DIM} fg="#525252">
            type to search... (Esc to clear)
          </text>
        )}
      </box>
    </box>
  );
}
