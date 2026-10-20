import React, { useEffect, useState } from 'react';
import { EYE_COLOR_FRAMES, FRAME_DELAYS_MS, type ColorLine } from '../assets/eyeFramesColor.ts';

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
    if (frameIdx >= EYE_COLOR_FRAMES.length - 1) {
      const timeout = setTimeout(() => {
        onComplete();
      }, 40);
      return () => clearTimeout(timeout);
    }

    const delay = FRAME_DELAYS_MS[frameIdx] ?? 20;
    const timeout = setTimeout(() => {
      setFrameIdx((i) => i + 1);
    }, delay);

    return () => clearTimeout(timeout);
  }, [frameIdx, onComplete]);

  const currentLines: ColorLine[] = EYE_COLOR_FRAMES[frameIdx] || [];

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
        {currentLines.map((line, lineIdx) => (
          <box key={lineIdx} flexDirection="row">
            {line.map(([text, color], spanIdx) => (
              <text key={spanIdx} color={color}>
                {text}
              </text>
            ))}
          </box>
        ))}
      </box>

      <box
        flexDirection="row"
        justifyContent="space-between"
        width={80}
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
