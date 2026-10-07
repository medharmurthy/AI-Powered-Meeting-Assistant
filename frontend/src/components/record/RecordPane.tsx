import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, X } from 'lucide-react';
import type { RunState } from '../../api/types';
import { RecordNav } from './RecordNav';
import { SummarySection } from './SummarySection';
import { MinutesSection } from './MinutesSection';
import { DecisionsSection } from './DecisionsSection';
import { UnresolvedSection } from './UnresolvedSection';
import { TasksSection } from './TasksSection';
import { ExportSection } from './ExportSection';
import { formatTime } from '../../lib/segments';

interface RecordPaneProps {
  run: RunState;
}

export const RecordPane: React.FC<RecordPaneProps> = ({ run }) => {
  const [showDroppedPopover, setShowDroppedPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showDroppedPopover) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowDroppedPopover(false);
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowDroppedPopover(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDroppedPopover]);

  const isDocRunning = run.status === 'running' && run.stage === 'document';
  const record = run.record || {};
  const dropped = record.dropped || [];
  const segments = run.raw || [];

  const title = record.title || run.filename || 'Meeting Record';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', position: 'relative' }}>
      {/* Header */}
      <header
        style={{
          padding: 'var(--s5) var(--s5) var(--s4) var(--s5)',
          borderBottom: '1px solid var(--rule)',
          background: 'var(--sheet)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 'var(--s3)' }}>
          <div>
            <h2
              style={{
                fontFamily: 'var(--font-doc)',
                fontSize: 'var(--t-xl)',
                fontWeight: 600,
                color: 'var(--ink)',
                marginBottom: 'var(--s1)',
                letterSpacing: '-0.02em',
              }}
            >
              {title}
            </h2>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--s2)',
                fontSize: 'var(--t-xs)',
                color: 'var(--ink-soft)',
                flexWrap: 'wrap',
              }}
            >
              <span>{run.filename}</span>
              {run.duration != null && run.duration > 0 && (
                <>
                  <span>·</span>
                  <span className="tabular-nums">{formatTime(run.duration)}</span>
                </>
              )}
            </div>
          </div>

          {/* Dropped items button */}
          {dropped.length > 0 && (
            <div style={{ position: 'relative' }}>
              <button
                type="button"
                onClick={() => setShowDroppedPopover(!showDroppedPopover)}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--ink-soft)',
                  fontSize: 'var(--t-xs)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  padding: '4px',
                }}
              >
                <ShieldAlert size={14} color="var(--alert)" />
                <span>
                  {dropped.length} model {dropped.length === 1 ? 'suggestion' : 'suggestions'} removed
                </span>
              </button>

              {/* Dropped items popover */}
              {showDroppedPopover && (
                <div
                  ref={popoverRef}
                  className="sheet"
                  role="dialog"
                  aria-label="Removed model suggestions"
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: '100%',
                    marginTop: '6px',
                    width: '320px',
                    maxHeight: '360px',
                    overflowY: 'auto',
                    padding: 'var(--s3)',
                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
                    zIndex: 20,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 'var(--s2)',
                      paddingBottom: 'var(--s1)',
                      borderBottom: '1px solid var(--rule)',
                    }}
                  >
                    <span style={{ fontWeight: 600, fontSize: 'var(--t-xs)' }}>
                      Removed by safety checks
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowDroppedPopover(false)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--ink-soft)',
                      }}
                    >
                      <X size={14} />
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s2)' }}>
                    {dropped.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: '11.5px',
                          padding: '6px 8px',
                          background: 'var(--paper)',
                          borderRadius: 'var(--r-ctl)',
                        }}
                      >
                        <div style={{ fontWeight: 600, color: 'var(--ink-soft)', textTransform: 'capitalize' }}>
                          {item.section}
                        </div>
                        <div style={{ color: 'var(--ink)', margin: '2px 0' }}>{item.text}</div>
                        <div style={{ color: 'var(--alert)', fontStyle: 'italic' }}>
                          Reason: {item.reason}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Sticky nav */}
      <RecordNav />

      {/* Sheet Content */}
      <div style={{ padding: 'var(--s5)' }}>
        <SummarySection
          summary={record.summary}
          attendees={record.attendees}
          isWriting={isDocRunning && !record.summary}
        />

        <MinutesSection
          topics={record.minutes}
          segments={segments}
          isWriting={isDocRunning && (!record.minutes || record.minutes.length === 0)}
        />

        <DecisionsSection
          decisions={record.decisions}
          segments={segments}
          isWriting={isDocRunning && (!record.decisions || record.decisions.length === 0)}
        />

        <UnresolvedSection
          unresolved={record.unresolved}
          segments={segments}
          isWriting={isDocRunning && (!record.unresolved || record.unresolved.length === 0)}
        />

        <TasksSection
          actions={record.action_items}
          segments={segments}
          isWriting={isDocRunning && (!record.action_items || record.action_items.length === 0)}
        />

        <ExportSection run={run} />
      </div>
    </div>
  );
};
