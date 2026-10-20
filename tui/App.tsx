import React, { useState, useMemo, useCallback } from 'react';
import { useKeyboard, useTerminalDimensions } from '@opentui/react';
import type { AgentInfo, AgentKey, ThreadItem, ViewMode } from './types.ts';
import { detectAgents, filterThreads, loadAllThreads } from './data.ts';
import { Header } from './components/Header.tsx';
import { ChatList } from './components/ChatList.tsx';
import { ChatDetail } from './components/ChatDetail.tsx';
import { AgentPicker } from './components/AgentPicker.tsx';
import { Footer } from './components/Footer.tsx';

interface AppProps {
  currentCwd: string;
  initialQuery?: string;
  onLaunch: (thread: ThreadItem, agentKey: AgentKey) => void;
  onExit: () => void;
}

export function App({ currentCwd, initialQuery = '', onLaunch, onExit }: AppProps) {
  const [allThreads, setAllThreads] = useState<ThreadItem[]>(() => loadAllThreads());
  const agents = useMemo<AgentInfo[]>(() => detectAgents(), []);

  // Determine initial scope
  const hasLocal = useMemo(() => {
    return filterThreads(allThreads, '', false, currentCwd).length > 0;
  }, [allThreads, currentCwd]);

  const [scopeAll, setScopeAll] = useState<boolean>(!hasLocal);
  const [searchQuery, setSearchQuery] = useState<string>(initialQuery);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [view, setView] = useState<ViewMode>('list');
  const [agentPickerIndex, setAgentPickerIndex] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>('');

  const dimensions = useTerminalDimensions();
  const height = dimensions.height || 30;

  // Filtered threads list
  const filteredThreads = useMemo(() => {
    return filterThreads(allThreads, searchQuery, scopeAll, currentCwd);
  }, [allThreads, searchQuery, scopeAll, currentCwd]);

  const selectedThread: ThreadItem | null =
    filteredThreads.length > 0
      ? filteredThreads[Math.min(selectedIndex, filteredThreads.length - 1)]
      : null;

  // Handle launching
  const doLaunch = useCallback(
    (thread: ThreadItem, agentKey: AgentKey) => {
      onLaunch(thread, agentKey);
    },
    [onLaunch]
  );

  // Keyboard navigation
  useKeyboard((key) => {
    if (key.ctrl && key.name === 'c') {
      onExit();
      return;
    }

    if (view === 'list') {
      if (key.name === 'escape') {
        if (searchQuery) {
          setSearchQuery('');
          setSelectedIndex(0);
        } else {
          onExit();
        }
        return;
      }

      if (key.name === 'up' || (key.ctrl && key.name === 'p')) {
        setSelectedIndex((i) => Math.max(0, i - 1));
        return;
      }

      if (key.name === 'down' || (key.ctrl && key.name === 'n')) {
        setSelectedIndex((i) => Math.min(filteredThreads.length - 1, i + 1));
        return;
      }

      if (key.name === 'pageup') {
        setSelectedIndex((i) => Math.max(0, i - 10));
        return;
      }

      if (key.name === 'pagedown') {
        setSelectedIndex((i) => Math.min(filteredThreads.length - 1, i + 10));
        return;
      }

      if (key.name === 'home') {
        setSelectedIndex(0);
        return;
      }

      if (key.name === 'end') {
        setSelectedIndex(Math.max(0, filteredThreads.length - 1));
        return;
      }

      if (key.name === 'tab') {
        setScopeAll((prev) => !prev);
        setSelectedIndex(0);
        return;
      }

      if (key.name === 'return') {
        if (selectedThread) {
          // Switch to agent picker
          // Find index of recent agent
          const recentIdx = agents.findIndex((a) => a.key === selectedThread.recentAgent);
          setAgentPickerIndex(recentIdx >= 0 ? recentIdx : 0);
          setView('agent-picker');
        }
        return;
      }

      if (key.name === 'backspace') {
        setSearchQuery((q) => q.slice(0, -1));
        setSelectedIndex(0);
        return;
      }

      // Quick sync hotkey
      if (!searchQuery && key.sequence === 's') {
        setStatusMessage('Syncing...');
        try {
          const reloaded = loadAllThreads();
          setAllThreads(reloaded);
          setStatusMessage('Synced chats!');
          setTimeout(() => setStatusMessage(''), 2000);
        } catch {
          setStatusMessage('Sync failed');
        }
        return;
      }

      // Append printable characters to search query
      if (key.sequence && key.sequence.length === 1 && !key.ctrl && !key.meta) {
        setSearchQuery((q) => q + key.sequence);
        setSelectedIndex(0);
        return;
      }
    } else if (view === 'agent-picker') {
      if (key.name === 'escape' || key.name === 'left' || key.name === 'backspace') {
        setView('list');
        return;
      }

      if (key.name === 'up' || (key.ctrl && key.name === 'p')) {
        setAgentPickerIndex((i) => Math.max(0, i - 1));
        return;
      }

      if (key.name === 'down' || (key.ctrl && key.name === 'n')) {
        setAgentPickerIndex((i) => Math.min(agents.length - 1, i + 1));
        return;
      }

      // Shortcut numbers 1-9
      if (key.sequence && /^[1-9]$/.test(key.sequence)) {
        const num = parseInt(key.sequence, 10);
        if (num >= 1 && num <= agents.length) {
          const chosen = agents[num - 1];
          if (selectedThread) {
            doLaunch(selectedThread, chosen.key);
          }
        }
        return;
      }

      if (key.name === 'return') {
        const chosen = agents[agentPickerIndex];
        if (selectedThread && chosen) {
          doLaunch(selectedThread, chosen.key);
        }
        return;
      }
    }
  });

  const maxVisibleChats = Math.max(5, height - 12);

  return (
    <box flexDirection="column" width="100%" height="100%" padding={0}>
      {/* Top Header */}
      <Header
        searchQuery={searchQuery}
        scopeAll={scopeAll}
        currentCwd={currentCwd}
        totalCount={allThreads.length}
        filteredCount={filteredThreads.length}
      />

      {/* Main Content Area */}
      {view === 'list' ? (
        <box flexDirection="row" flexGrow={1} width="100%" gap={1} marginTop={0}>
          <ChatList
            threads={filteredThreads}
            selectedIndex={selectedIndex}
            maxVisible={maxVisibleChats}
            scopeAll={scopeAll}
          />
          <ChatDetail thread={selectedThread} agents={agents} />
        </box>
      ) : (
        <box flexDirection="column" flexGrow={1} width="100%" marginTop={0}>
          {selectedThread && (
            <AgentPicker
              thread={selectedThread}
              agents={agents}
              selectedIndex={agentPickerIndex}
            />
          )}
        </box>
      )}

      {/* Footer Status & Keys */}
      <Footer view={view} statusMessage={statusMessage} />
    </box>
  );
}
