import React, { useState } from 'react';
import { useLocation } from 'wouter';
import { Clock, ChevronRight, Trash2, Check, X } from 'lucide-react';
import type { RunSummary } from '../../api/types';
import { deleteRun } from '../../api/client';
import { formatTime } from '../../lib/segments';

interface RecentRunsProps {
  runs: RunSummary[];
  onDeleted?: (runId: string) => void;
}

export const RecentRuns: React.FC<RecentRunsProps> = ({ runs, onDeleted }) => {
  const [, setLocation] = useLocation();
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const visibleRuns = runs.filter((r) => !deletedIds.has(r.id));
  if (visibleRuns.length === 0) return null;

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    } catch {
      return '';
    }
  };

  const handleStartDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setConfirmDeleteId(id);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirmDeleteId(null);
  };

  const handleConfirmDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setIsDeleting(true);
    try {
      await deleteRun(id);
      setDeletedIds((prev) => new Set(prev).add(id));
      onDeleted?.(id);
    } catch (err) {
      console.error('Failed to delete run', err);
    } finally {
      setIsDeleting(false);
      setConfirmDeleteId(null);
    }
  };

  return (
    <section style={{ marginTop: 'var(--s6)' }}>
      <h2
        style={{
          fontSize: 'var(--t-sm)',
          fontWeight: 600,
          marginBottom: 'var(--s3)',
          color: 'var(--ink-soft)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        Recent recordings
      </h2>

      <div className="sheet" style={{ overflow: 'hidden' }}>
        {visibleRuns.map((r, i) => (
          <div
            key={r.id}
            role="button"
            tabIndex={0}
            onClick={() => setLocation(`/r/${r.id}`)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setLocation(`/r/${r.id}`);
              }
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--s3) var(--s4)',
              borderBottom: i < visibleRuns.length - 1 ? '1px solid var(--rule)' : 'none',
              cursor: 'pointer',
              transition: 'background-color 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--paper)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s3)', minWidth: 0, flex: 1 }}>
              <Clock size={16} color="var(--ink-soft)" style={{ flexShrink: 0 }} />
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--s2)', minWidth: 0, flexWrap: 'wrap' }}>
                <span
                  style={{
                    fontWeight: 600,
                    fontSize: 'var(--t-sm)',
                    color: 'var(--ink)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {r.title || r.filename}
                </span>
                <span style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>·</span>
                {r.duration != null && r.duration > 0 && (
                  <>
                    <span className="tabular-nums" style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>
                      {formatTime(r.duration)}
                    </span>
                    <span style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>·</span>
                  </>
                )}
                <span
                  style={{
                    fontSize: 'var(--t-xs)',
                    color: r.status === 'done' ? 'var(--ok)' : r.status === 'failed' ? 'var(--alert)' : 'var(--blue)',
                    textTransform: 'capitalize',
                  }}
                >
                  {r.status}
                </span>
                {r.created_at && (
                  <>
                    <span style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>·</span>
                    <span style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>
                      {formatDate(r.created_at)}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Action buttons: Delete / Confirm Delete / Chevron */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)', flexShrink: 0 }} onClick={(e) => e.stopPropagation()}>
              {confirmDeleteId === r.id ? (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    background: 'var(--alert-wash)',
                    padding: '2px 8px',
                    borderRadius: 'var(--r-ctl)',
                    border: '1px solid var(--alert)',
                    fontSize: '11.5px',
                  }}
                >
                  <span style={{ color: 'var(--alert)', fontWeight: 600 }}>Delete?</span>
                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={(e) => handleConfirmDelete(e, r.id)}
                    title="Confirm deletion"
                    aria-label="Confirm deletion"
                    style={{
                      background: 'var(--alert)',
                      color: '#FFFFFF',
                      border: 'none',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '2px',
                    }}
                  >
                    <Check size={12} />
                    <span>Yes</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelDelete}
                    title="Cancel deletion"
                    aria-label="Cancel deletion"
                    style={{
                      background: 'none',
                      border: '1px solid var(--rule)',
                      color: 'var(--ink-soft)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                      display: 'inline-flex',
                      alignItems: 'center',
                    }}
                  >
                    <X size={12} />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={(e) => handleStartDelete(e, r.id)}
                  title="Delete recording"
                  aria-label="Delete recording"
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--ink-soft)',
                    padding: '4px',
                    borderRadius: 'var(--r-ctl)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'color 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--alert)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--ink-soft)';
                  }}
                >
                  <Trash2 size={15} />
                </button>
              )}

              <ChevronRight size={16} color="var(--ink-soft)" style={{ flexShrink: 0 }} />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
