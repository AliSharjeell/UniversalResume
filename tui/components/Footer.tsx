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
      borderStyle="single"
      borderColor="#1E293B"
      paddingLeft={1}
      paddingRight={1}
      width="100%"
    >
      {view === 'list' ? (
        <box flexDirection="row" gap={2}>
          <box flexDirection="row" gap={1}>
            <text bold color="#38BDF8">[↑/↓]</text>
            <text color="#94A3B8">Navigate</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#10B981">[Enter]</text>
            <text color="#94A3B8">Resume</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#F59E0B">[Tab]</text>
            <text color="#94A3B8">Scope</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#A855F7">[s]</text>
            <text color="#94A3B8">Sync</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#EF4444">[Esc]</text>
            <text color="#94A3B8">Quit</text>
          </box>
        </box>
      ) : (
        <box flexDirection="row" gap={2}>
          <box flexDirection="row" gap={1}>
            <text bold color="#38BDF8">[1-9]</text>
            <text color="#94A3B8">Quick Pick</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#38BDF8">[↑/↓]</text>
            <text color="#94A3B8">Navigate</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#10B981">[Enter]</text>
            <text color="#94A3B8">Launch</text>
          </box>
          <box flexDirection="row" gap={1}>
            <text bold color="#EF4444">[Esc]</text>
            <text color="#94A3B8">Back</text>
          </box>
        </box>
      )}

      {statusMessage ? (
        <text color="#F59E0B">{statusMessage}</text>
      ) : (
        <text dim color="#475569">SameThread v0.3.0</text>
      )}
    </box>
  );
}
