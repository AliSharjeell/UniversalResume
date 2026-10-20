import React, { useEffect, useState } from 'react';
import { EYE_FRAMES, FRAME_DELAYS_MS } from '../assets/eyeFrames.ts';

interface EyeStartupTransitionProps {
  onComplete: () => void;
  isSyncing: boolean;
}

export function EyeStartupTransition({
  onComplete,
  isSyncing,
}: EyeStartupTransitionProps) {
  const [frameIdx, setFrameIdx] = useState<number>(0);

  useEffect(() => {
    if (frameIdx >= EYE_FRAMES.length - 1) {
      // Small pause on final black frame before revealing TUI
      const timeout = setTimeout(() => {
        onComplete();
      }, 50);
      return () => clearTimeout(timeout);
    }

    const delay = FRAME_DELAYS_MS[frameIdx] ?? 25;
    const timeout = setTimeout(() => {
      setFrameIdx((i) => i + 1);
    }, delay);

    return () => clearTimeout(timeout);
  }, [frameIdx, onComplete]);

  const currentLines = EYE_FRAMES[frameIdx] || [];

  return (
    <box
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      flexGrow={1}
      width="100%"
      height="100%"
    >
      <box flexDirection="column">
        {currentLines.map((line, idx) => (
          <text key={idx} color="#FFFFFF">
            {line}
          </text>
        ))}
      </box>

      <box
        flexDirection="row"
        justifyContent="space-between"
        width={68}
        marginTop={1}
      >
        <text color="#737373">
          {isSyncing ? 'Syncing coding sessions...' : 'UNIVERSAL RESUME'}
        </text>
        <text dim color="#525252">
          Press any key to skip
        </text>
      </box>
    </box>
  );
}
