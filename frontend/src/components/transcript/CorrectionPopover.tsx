import React, { useState } from 'react';
import type { Correction } from '../../api/types';
import { patchCorrection } from '../../api/client';
import { useRunStore } from '../../state/runStore';

interface CorrectionPopoverProps {
  runId: string;
  correction: Correction;
  onClose: () => void;
  style?: React.CSSProperties;
}

export const CorrectionPopover: React.FC<CorrectionPopoverProps> = ({
  runId,
  correction,
  onClose,
  style,
}) => {
  const [isUpdating, setIsUpdating] = useState(false);
  const isApplied = correction.status === 'applied';

  const handleToggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isUpdating) return;
    setIsUpdating(true);

    const nextApplied = !isApplied;
    try {
      await patchCorrection(runId, correction.id, nextApplied);

      // Update current run in runStore directly so refined view and stale banner react immediately
      const runStore = useRunStore.getState();
      const cur = runStore.currentRun;
      if (cur) {
        const nextCorrections = cur.corrections.map((c) =>
          c.id === correction.id
            ? { ...c, status: (nextApplied ? 'applied' : 'reverted') as any }
            : c
        );

        // Update refined text segment if present
        const nextRefined = cur.refined?.map((seg) => {
          if (seg.id === correction.segment_id) {
            // If toggling off, revert text; if toggling on, apply
            const newText = nextApplied
              ? seg.text.replace(correction.original, correction.corrected)
              : seg.text.replace(correction.corrected, correction.original);
            return { ...seg, text: newText };
          }
          return seg;
        });

        useRunStore.setState({
          currentRun: {
            ...cur,
            corrections: nextCorrections,
            refined: nextRefined || cur.refined,
            recordStale: true,
          },
        });
      }
    } catch (err) {
      console.error('Failed to toggle correction', err);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div
      role="tooltip"
      className="sheet"
      onClick={(e) => e.stopPropagation()}
      style={{
        position: 'absolute',
        zIndex: 50,
        padding: '10px 14px',
        width: '260px',
        boxShadow: '0 6px 20px rgba(0, 0, 0, 0.15)',
        borderRadius: 'var(--r-ctl)',
        border: '1px solid var(--rule)',
        background: 'var(--sheet)',
        fontSize: 'var(--t-xs)',
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontWeight: 600, color: 'var(--ink-soft)', fontSize: '11px', textTransform: 'uppercase' }}>
          Term Correction
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--ink-soft)',
            cursor: 'pointer',
            padding: 0,
            fontSize: '13px',
          }}
          aria-label="Close"
        >
          ×
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '4px', flexWrap: 'wrap' }}>
        <span className="del-mark" style={{ color: 'var(--ink-soft)' }}>
          {correction.original}
        </span>
        <span style={{ color: 'var(--ink-soft)' }}>→</span>
        <span className="ins-mark" style={{ fontWeight: 600, color: 'var(--blue)' }}>
          {correction.corrected}
        </span>
      </div>

      <div style={{ color: 'var(--ink-soft)', fontSize: '11px', lineHeight: 1.4, marginBottom: '10px' }}>
        {correction.reason}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderTop: '1px solid var(--rule)',
          paddingTop: '8px',
        }}
      >
        <label
          htmlFor={`toggle-${correction.id}`}
          style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--ink)', cursor: 'pointer' }}
        >
          Applied
        </label>
        <button
          id={`toggle-${correction.id}`}
          type="button"
          role="switch"
          aria-checked={isApplied}
          onClick={handleToggle}
          disabled={isUpdating}
          style={{
            position: 'relative',
            width: '36px',
            height: '20px',
            borderRadius: '10px',
            border: 'none',
            background: isApplied ? 'var(--blue)' : 'var(--rule)',
            cursor: isUpdating ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s ease',
            padding: 0,
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '2px',
              left: isApplied ? '18px' : '2px',
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              backgroundColor: '#FFFFFF',
              boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
              transition: 'left 0.2s ease',
            }}
          />
        </button>
      </div>
    </div>
  );
};
