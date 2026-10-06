import React from 'react';
import { Play } from 'lucide-react';
import { useFocusStore } from '../../state/focusStore';
import { usePlayerStore } from '../../state/playerStore';
import { formatTime, rangeFor } from '../../lib/segments';
import type { Segment } from '../../api/types';

interface EvidenceChipProps {
  segmentIds: number[];
  segments?: Segment[];
}

export const EvidenceChip: React.FC<EvidenceChipProps> = ({ segmentIds, segments = [] }) => {
  const { hoverIds, pinnedIds, setHover, clearHover, togglePin } = useFocusStore();
  const { playRange, setActiveRegion } = usePlayerStore();

  if (!segmentIds || segmentIds.length === 0) return null;

  const firstId = segmentIds[0];
  const firstSeg = segments.find((s) => s.id === firstId);
  const startTime = firstSeg ? firstSeg.start : 0;
  const timeLabel = formatTime(startTime);
  const extraCount = segmentIds.length - 1;

  const isPinned = pinnedIds.length > 0 && segmentIds.some((id) => pinnedIds.includes(id));
  const isHovered = hoverIds.length > 0 && segmentIds.some((id) => hoverIds.includes(id));

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    const willPin = !isPinned;
    togglePin(segmentIds);

    if (willPin) {
      // 1. Calculate bounding time range for cited segments
      const range = rangeFor(segmentIds, segments);
      if (range) {
        const [minStart, maxEnd] = range;
        playRange(Math.max(0, minStart - 1.0), maxEnd + 0.5);
      } else if (firstSeg) {
        playRange(Math.max(0, firstSeg.start - 1.0), firstSeg.end + 0.5);
      }

      // 2. Scroll the first cited line into view in transcript
      const el = document.getElementById(`seg-${firstId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    } else {
      setActiveRegion(null);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      onMouseEnter={() => setHover(segmentIds)}
      onMouseLeave={clearHover}
      onFocus={() => setHover(segmentIds)}
      onBlur={clearHover}
      title={`Cites segment ${segmentIds.join(', ')}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 7px',
        borderRadius: 'var(--r-chip)',
        fontSize: '11.5px',
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        background: isPinned
          ? 'var(--marker)'
          : isHovered
          ? 'var(--marker-wash)'
          : 'var(--paper)',
        color: isPinned ? '#16222B' : 'var(--ink-soft)',
        border: `1px solid ${isPinned ? 'var(--marker)' : isHovered ? 'var(--marker)' : 'var(--rule)'}`,
        whiteSpace: 'nowrap',
      }}
    >
      <Play size={9} style={{ fill: 'currentColor' }} />
      <span className="tabular-nums">{timeLabel}</span>
      {extraCount > 0 && (
        <span style={{ opacity: 0.85, fontSize: '10.5px' }}>+{extraCount}</span>
      )}
    </button>
  );
};
