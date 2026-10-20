import React from 'react';
import type { ViewMode } from '../types.ts';

interface FooterProps {
  view: ViewMode;
  statusMessage?: string;
}

export function Footer({ view, statusMessage }: FooterProps) {
  return (
    <box
      flexDirection="row"
      justifyContent="space-between"
      borderTop
      borderColor="#334155"
      paddingTop={1}
      width="100%"
    >
      {view === 'list' ? (
        <text color="#64748B">
          [↑/↓] Select   [Enter] Pick Agent   [Tab] Switch Scope   [s] Sync   [Esc] Quit
        </text>
      ) : (
        <text color="#64748B">
          [1-9] Quick Pick   [↑/↓] Select   [Enter] Launch   [Esc] Back to List
        </text>
      )}

      {statusMessage ? (
        <text color="#F59E0B">{statusMessage}</text>
      ) : (
        <text dim color="#475569">Universal Resume</text>
      )}
    </box>
  );
}
