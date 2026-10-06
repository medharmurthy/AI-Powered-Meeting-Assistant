import React, { useState } from 'react';
import type { Correction, Segment, Span } from '../../api/types';
import { useFocusStore } from '../../state/focusStore';
import { usePlayerStore } from '../../state/playerStore';
import { formatTime } from '../../lib/segments';
import { CorrectionPopover } from './CorrectionPopover';

interface SegmentRowProps {
  segment: Segment;
  spans?: Span[];
  corrections?: Correction[];
  runId?: string;
  isLatest?: boolean;
  isStreaming?: boolean;
  searchQuery?: string;
  onTimeClick?: (time: number) => void;
}

export const SegmentRow: React.FC<SegmentRowProps> = ({
  segment,
  spans,
  corrections = [],
  runId = '',
  isLatest,
  isStreaming,
  searchQuery,
  onTimeClick,
}) => {
  const { hoverIds, pinnedIds } = useFocusStore();
  const currentTime = usePlayerStore((s) => s.time);
  const seek = usePlayerStore((s) => s.seek);

  const [activeCorrection, setActiveCorrection] = useState<Correction | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(null);

  const isPinned = pinnedIds.includes(segment.id);
  const isHovered = hoverIds.includes(segment.id);
  const isActive = currentTime >= segment.start && currentTime <= segment.end;

  const handleGutterClick = () => {
    seek(segment.start);
    onTimeClick?.(segment.start);
  };

  const handleSpanClick = (e: React.MouseEvent, cid: string) => {
    e.stopPropagation();
    const corr = corrections.find((c) => c.id === cid);
    if (corr) {
      const rect = e.currentTarget.getBoundingClientRect();
      setPopoverPos({ x: rect.left, y: rect.bottom + window.scrollY + 4 });
      setActiveCorrection(corr);
    }
  };

  // Render text with spans if present (Refined view)
  const renderSpannedText = (text: string, currentSpans: Span[]) => {
    if (!currentSpans || currentSpans.length === 0) {
      return renderHighlightedText(text, searchQuery);
    }

    const elements: React.ReactNode[] = [];
    let lastIdx = 0;

    // Sort spans by start offset
    const sortedSpans = [...currentSpans].sort((a, b) => a.start - b.start);

    sortedSpans.forEach((sp, idx) => {
      if (sp.start > lastIdx) {
        elements.push(
          <span key={`text-${idx}`}>{renderHighlightedText(text.slice(lastIdx, sp.start), searchQuery)}</span>
        );
      }

      const spanText = text.slice(sp.start, sp.end);
      elements.push(
        <ins
          key={`span-${idx}`}
          className="ins-mark"
          onClick={(e) => handleSpanClick(e, sp.correction_id)}
          style={{
            cursor: 'pointer',
            backgroundColor: 'var(--blue-wash)',
            borderRadius: '2px',
            padding: '0 2px',
          }}
          title="Click to view or toggle term correction"
        >
          {spanText}
        </ins>
      );
      lastIdx = sp.end;
    });

    if (lastIdx < text.length) {
      elements.push(<span key="text-end">{renderHighlightedText(text.slice(lastIdx), searchQuery)}</span>);
    }

    return elements;
  };

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

  // Render words with live spoken styling if words array is present
  const renderWords = () => {
    if (!segment.words || segment.words.length === 0) {
      return renderSpannedText(segment.text, spans || []);
    }

    return segment.words.map((word, wIdx) => {
      const isSpoken = currentTime >= word.start;
      return (
        <span
          key={wIdx}
          style={{
            color: isSpoken ? 'var(--ink)' : 'var(--ink-soft)',
            fontWeight: isSpoken ? 500 : 400,
            transition: 'color 0.1s ease',
          }}
        >
          {word.w}{' '}
        </span>
      );
    });
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
          : isActive
          ? '3px solid var(--blue)'
          : isHovered
          ? '3px solid var(--marker)'
          : '3px solid transparent',
        backgroundColor: isPinned
          ? 'var(--marker-wash)'
          : isHovered
          ? 'var(--marker-wash)'
          : isActive
          ? 'var(--blue-wash)'
          : 'transparent',
        transition: 'background-color 0.15s ease, border-color 0.15s ease',
        lineHeight: 1.6,
        position: 'relative',
      }}
    >
      {/* Time Gutter (60 px) */}
      <button
        type="button"
        onClick={handleGutterClick}
        title={`Click to seek and play from ${formatTime(segment.start)}`}
        style={{
          width: '60px',
          flexShrink: 0,
          background: 'none',
          border: 'none',
          padding: 0,
          textAlign: 'left',
          cursor: 'pointer',
          color: isActive ? 'var(--blue)' : 'var(--ink-soft)',
          fontWeight: isActive ? 700 : 400,
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
        {isActive && segment.words && segment.words.length > 0
          ? renderWords()
          : renderSpannedText(segment.text, spans || [])}

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

      {/* Active Correction Popover */}
      {activeCorrection && popoverPos && (
        <CorrectionPopover
          runId={runId}
          correction={activeCorrection}
          onClose={() => setActiveCorrection(null)}
          style={{
            top: '100%',
            left: '60px',
            marginTop: '4px',
          }}
        />
      )}
    </div>
  );
};
