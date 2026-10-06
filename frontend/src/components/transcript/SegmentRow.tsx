import React from 'react';
import type { Segment } from '../../api/types';
import { useFocusStore } from '../../state/focusStore';
import { formatTime } from '../../lib/segments';

interface SegmentRowProps {
  segment: Segment;
  isLatest?: boolean;
  isStreaming?: boolean;
  searchQuery?: string;
  onTimeClick?: (time: number) => void;
}

export const SegmentRow: React.FC<SegmentRowProps> = ({
  segment,
  isLatest,
  isStreaming,
  searchQuery,
  onTimeClick,
}) => {
  const { hoverIds, pinnedIds } = useFocusStore();

  const isPinned = pinnedIds.includes(segment.id);
  const isHovered = hoverIds.includes(segment.id);

  // Render text with search highlight if query exists
  const renderHighlightedText = (text: string, query?: string) => {
    if (!query || !query.trim()) return text;
    const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <mark
          key={i}
          style={{
            backgroundColor: 'var(--marker)',
            color: '#16222B',
            padding: '0 2px',
            borderRadius: '2px',
          }}
        >
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  return (
    <div
      id={`seg-${segment.id}`}
      style={{
        display: 'flex',
        alignItems: 'baseline',
        padding: '6px 12px',
        borderLeft: isPinned
          ? '3px solid var(--marker)'
          : isHovered
          ? '3px solid var(--marker)'
          : '3px solid transparent',
        backgroundColor: isPinned
          ? 'var(--marker-wash)'
          : isHovered
          ? 'var(--marker-wash)'
          : 'transparent',
        transition: 'background-color 0.15s ease, border-color 0.15s ease',
        lineHeight: 1.6,
      }}
    >
      {/* Time Gutter (60 px) */}
      <button
        type="button"
        onClick={() => onTimeClick?.(segment.start)}
        title={`Jump to ${formatTime(segment.start)}`}
        style={{
          width: '60px',
          flexShrink: 0,
          background: 'none',
          border: 'none',
          padding: 0,
          textAlign: 'left',
          cursor: 'pointer',
          color: 'var(--ink-soft)',
          fontSize: 'var(--t-xs)',
          fontFamily: 'var(--font-ui)',
        }}
        className="tabular-nums"
      >
        {formatTime(segment.start)}
      </button>

      {/* Speaker (if present) */}
      {segment.speaker && (
        <span
          style={{
            fontWeight: 700,
            fontSize: 'var(--t-xs)',
            color: 'var(--ink-soft)',
            marginRight: '8px',
            flexShrink: 0,
          }}
        >
          {segment.speaker}:
        </span>
      )}

      {/* Segment Text in Literata */}
      <span
        className="font-doc"
        style={{
          fontSize: '15.5px',
          color: 'var(--ink)',
          flex: 1,
        }}
      >
        {renderHighlightedText(segment.text, searchQuery)}
        {isLatest && isStreaming && (
          <span
            aria-hidden="true"
            style={{
              display: 'inline-block',
              width: '2px',
              height: '14px',
              marginLeft: '4px',
              backgroundColor: 'var(--blue)',
              verticalAlign: 'middle',
              animation: 'caretBlink 1s infinite',
            }}
          />
        )}
      </span>
    </div>
  );
};
