import React, { useEffect, useState, useMemo } from 'react';
import {
  EYE_COLOR_FRAMES,
  FRAME_DELAYS_MS,
  FRAME_WIDTH,
  FRAME_HEIGHT,
  type ColorLine,
  type ColorSpan,
} from '../assets/eyeFramesColor.ts';

interface EyeStartupTransitionProps {
  onComplete: () => void;
  width?: number;
  height?: number;
}

function sliceLineSpans(line: ColorLine, startX: number, endX: number): ColorSpan[] {
  const result: ColorSpan[] = [];
  let currentPos = 0;

  for (let i = 0; i < line.length; i++) {
    const [text, color] = line[i];
    const spanStart = currentPos;
    const spanEnd = currentPos + text.length;
    currentPos = spanEnd;

    // Check overlap with [startX, endX)
    if (spanEnd <= startX || spanStart >= endX) {
      continue;
    }

    const sliceFrom = Math.max(0, startX - spanStart);
    const sliceTo = Math.min(text.length, endX - spanStart);
    const slicedText = text.slice(sliceFrom, sliceTo);

    if (slicedText.length > 0) {
      result.push([slicedText, color]);
    }
  }

  return result;
}

export function EyeStartupTransition({
  onComplete,
  width = 100,
  height = 26,
}: EyeStartupTransitionProps) {
  const [frameIdx, setFrameIdx] = useState<number>(0);

  useEffect(() => {
    if (frameIdx >= EYE_COLOR_FRAMES.length - 1) {
      const timeout = setTimeout(() => {
        onComplete();
      }, 30);
      return () => clearTimeout(timeout);
    }

    const delay = FRAME_DELAYS_MS[frameIdx] ?? 20;
    const timeout = setTimeout(() => {
      setFrameIdx((i) => i + 1);
    }, delay);

    return () => clearTimeout(timeout);
  }, [frameIdx, onComplete]);

  const rawLines: ColorLine[] = EYE_COLOR_FRAMES[frameIdx] || [];

  // Fullscreen responsive fitting without wrapping
  const visibleLines = useMemo(() => {
    const maxCols = Math.max(40, width);
    const maxRows = Math.max(15, height);

    let startX = 0;
    let endX = FRAME_WIDTH;
    if (maxCols < FRAME_WIDTH) {
      startX = Math.floor((FRAME_WIDTH - maxCols) / 2);
      endX = startX + maxCols;
    }

    let startY = 0;
    let endY = FRAME_HEIGHT;
    if (maxRows < FRAME_HEIGHT) {
      startY = Math.floor((FRAME_HEIGHT - maxRows) / 2);
      endY = startY + maxRows;
    }

    const croppedRows = rawLines.slice(startY, endY);
    return croppedRows.map((line) => sliceLineSpans(line, startX, endX));
  }, [rawLines, width, height]);

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
        {visibleLines.map((line, lineIdx) => (
          <box key={lineIdx} flexDirection="row">
            {line.map(([text, color], spanIdx) => (
              <text key={spanIdx} color={color}>
                {text}
              </text>
            ))}
          </box>
        ))}
      </box>
    </box>
  );
}
