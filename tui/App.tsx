import React, { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import { useKeyboard, useTerminalDimensions } from '@opentui/react';
import type { AgentInfo, AgentKey, ThreadItem, ViewMode } from './types.ts';
import { detectAgents, filterThreads, loadAllThreads, runSync } from './data.ts';
import { Header } from './components/Header.tsx';
import { ChatList } from './components/ChatList.tsx';
import { AgentPicker } from './components/AgentPicker.tsx';

interface AppProps {
  currentCwd: string;
  initialQuery?: string;
  onLaunch: (thread: ThreadItem, agentKey: AgentKey) => void;
  onExit: () => void;
}

export function App({ currentCwd, initialQuery = '', onLaunch, onExit }: AppProps) {
  const [allThreads, setAllThreads] = useState<ThreadItem[]>(() => loadAllThreads());
  const agents = useMemo<AgentInfo[]>(() => detectAgents(), []);

  // Counts
  const inFolderCount = useMemo(() => {
    return filterThreads(allThreads, '', false, currentCwd).length;
  }, [allThreads, currentCwd]);

  const globalCount = allThreads.length;

  const [scopeAll, setScopeAll] = useState<boolean>(inFolderCount === 0);
  const [searchQuery, setSearchQuery] = useState<string>(initialQuery);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [view, setView] = useState<ViewMode>('list');
  const [agentPickerIndex, setAgentPickerIndex] = useState<number>(0);
  const [pickerError, setPickerError] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const isSyncingRef = useRef<boolean>(false);

  const dimensions = useTerminalDimensions();
  const height = dimensions.height || 24;
  const width = dimensions.width || 80;

  // Filtered list
  const filteredThreads = useMemo(() => {
    return filterThreads(allThreads, searchQuery, scopeAll, currentCwd);
  }, [allThreads, searchQuery, scopeAll, currentCwd]);

  const selectedThread: ThreadItem | null =
    filteredThreads.length > 0 && selectedIndex >= 0
      ? filteredThreads[Math.max(0, Math.min(selectedIndex, filteredThreads.length - 1))]
      : null;

  // Background sync
  const handleSync = useCallback(async () => {
    if (isSyncingRef.current) return;
    isSyncingRef.current = true;
    setIsSyncing(true);
    setStatusMessage('Syncing...');
    try {
      await runSync();
      const updated = loadAllThreads();
      setAllThreads(updated);
      setStatusMessage('Synced');
    } catch {
      setStatusMessage('Sync failed');
    } finally {
      isSyncingRef.current = false;
      setIsSyncing(false);
      setTimeout(() => setStatusMessage(''), 2500);
    }
  }, []);

  // Auto-sync on startup
  useEffect(() => {
    handleSync();
  }, [handleSync]);

  const doLaunch = useCallback(
    (thread: ThreadItem, agentKey: AgentKey) => {
      onLaunch(thread, agentKey);
    },
    [onLaunch]
  );

  // Keyboard controls
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
          const recentIdx = agents.findIndex((a) => a.key === selectedThread.recentAgent);
          setAgentPickerIndex(recentIdx >= 0 ? recentIdx : 0);
          setPickerError('');
          setView('agent-picker');
        }
        return;
      }

      if (key.name === 'backspace') {
        setSearchQuery((q) => q.slice(0, -1));
        setSelectedIndex(0);
        return;
      }

      // Manual sync hotkey
      if (key.ctrl && key.name === 's') {
        handleSync();
        return;
      }

      // Printable characters
      if (key.sequence && key.sequence.length === 1 && !key.ctrl && !key.meta) {
        setSearchQuery((q) => q + key.sequence);
        setSelectedIndex(0);
        return;
      }
    } else if (view === 'agent-picker') {
      if (key.name === 'escape' || key.name === 'left' || key.name === 'backspace') {
        setView('list');
        setPickerError('');
        return;
      }

      if (key.name === 'up' || (key.ctrl && key.name === 'p')) {
        setAgentPickerIndex((i) => Math.max(0, i - 1));
        setPickerError('');
        return;
      }

      if (key.name === 'down' || (key.ctrl && key.name === 'n')) {
        setAgentPickerIndex((i) => Math.min(agents.length - 1, i + 1));
        setPickerError('');
        return;
      }

      // Quick pick numbers 1-9
      if (key.sequence && /^[1-9]$/.test(key.sequence)) {
        const num = parseInt(key.sequence, 10);
        if (num >= 1 && num <= agents.length) {
          const chosen = agents[num - 1];
          if (!chosen.installed) {
            setPickerError(`${chosen.name} is not installed`);
            return;
          }
          if (selectedThread) {
            doLaunch(selectedThread, chosen.key);
          }
        }
        return;
      }

      if (key.name === 'return') {
        const chosen = agents[agentPickerIndex];
        if (chosen && !chosen.installed) {
          setPickerError(`${chosen.name} is not installed`);
          return;
        }
        if (selectedThread && chosen) {
          doLaunch(selectedThread, chosen.key);
        }
        return;
      }
    }
  });

  const folderName = currentCwd.split(/[\\/]/).filter(Boolean).pop() || currentCwd;
  const maxVisibleChats = Math.max(5, height - 8);

  return (
    <box
      flexDirection="column"
      width="100%"
      height="100%"
      borderStyle="rounded"
      borderColor="#404040"
      padding={1}
    >
      {view === 'list' ? (
        <>
          <Header
            searchQuery={searchQuery}
            scopeAll={scopeAll}
            inFolderCount={inFolderCount}
            globalCount={globalCount}
            isSyncing={isSyncing}
            folderName={folderName}
            onToggleScope={() => {
              setScopeAll((prev) => !prev);
              setSelectedIndex(0);
            }}
            onTriggerSync={handleSync}
          />
          <ChatList
            threads={filteredThreads}
            selectedIndex={selectedIndex}
            maxVisible={maxVisibleChats}
            scopeAll={scopeAll}
            termWidth={width}
            onSelect={(idx) => setSelectedIndex(idx)}
            onChoose={(th) => {
              const recentIdx = agents.findIndex((a) => a.key === th.recentAgent);
              setAgentPickerIndex(recentIdx >= 0 ? recentIdx : 0);
              setPickerError('');
              setView('agent-picker');
            }}
          />
        </>
      ) : (
        selectedThread && (
          <AgentPicker
            thread={selectedThread}
            agents={agents}
            selectedIndex={agentPickerIndex}
            errorMessage={pickerError}
            onSelect={(agentKey) => {
              const chosen = agents.find((a) => a.key === agentKey);
              if (chosen && !chosen.installed) {
                setPickerError(`${chosen.name} is not installed`);
                return;
              }
              doLaunch(selectedThread, agentKey);
            }}
          />
        )
      )}
    </box>
  );
}
