import React, { useState } from 'react';
import type { RefinedSegment, Segment } from '../../api/types';
import { formatTime } from '../../lib/segments';

interface CompareRowProps {
  segmentId: number;
  rawText: string;
  refinedText: string;
  start: number;
  isModified: boolean;
  onTimeClick?: (time: number) => void;
}

export const CompareRow: React.FC<CompareRowProps> = ({
  rawText,
  refinedText,
  start,
  isModified,
  onTimeClick,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'baseline',
        padding: '6px 12px',
        borderBottom: '1px solid var(--rule)',
        backgroundColor: isModified ? 'var(--blue-wash)' : 'transparent',
        fontSize: '14.5px',
        lineHeight: 1.5,
      }}
    >
      {/* Time gutter */}
      <button
        type="button"
        onClick={() => onTimeClick?.(start)}
        title={`Jump to ${formatTime(start)}`}
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
        }}
        className="tabular-nums"
      >
        {formatTime(start)}
      </button>

      {/* Raw column (left 50%) */}
      <div
        className="font-doc"
        style={{
          flex: 1,
          paddingRight: 'var(--s3)',
          borderRight: '1px solid var(--rule)',
          color: isModified ? 'var(--ink-soft)' : 'var(--ink)',
        }}
      >
        {rawText}
      </div>

      {/* Refined column (right 50%) */}
      <div
        className="font-doc"
        style={{
          flex: 1,
          paddingLeft: 'var(--s3)',
          color: 'var(--ink)',
          fontWeight: isModified ? 600 : 'normal',
        }}
      >
        {refinedText}
      </div>
    </div>
  );
};

interface CollapsedUnchangedProps {
  count: number;
  segments: { raw: Segment; refined: RefinedSegment }[];
  onTimeClick?: (time: number) => void;
}

export const CollapsedUnchanged: React.FC<CollapsedUnchangedProps> = ({
  count,
  segments,
  onTimeClick,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (isExpanded) {
    return (
      <div>
        <button
          type="button"
          onClick={() => setIsExpanded(false)}
          style={{
            width: '100%',
            textAlign: 'center',
            padding: '4px',
            background: 'var(--paper)',
            border: 'none',
            borderBottom: '1px solid var(--rule)',
            color: 'var(--ink-soft)',
            fontSize: 'var(--t-xs)',
            cursor: 'pointer',
          }}
        >
          Collapse {count} unchanged lines ▲
        </button>
        {segments.map(({ raw, refined }) => (
          <CompareRow
            key={raw.id}
            segmentId={raw.id}
            rawText={raw.text}
            refinedText={refined.text}
            start={raw.start}
            isModified={false}
            onTimeClick={onTimeClick}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      onClick={() => setIsExpanded(true)}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '8px 12px',
        backgroundColor: 'var(--paper)',
        borderBottom: '1px solid var(--rule)',
        color: 'var(--ink-soft)',
        fontSize: 'var(--t-xs)',
        cursor: 'pointer',
        fontStyle: 'italic',
      }}
    >
      <span>{count} {count === 1 ? 'line' : 'lines'} unchanged (click to expand)</span>
    </div>
  );
};
