import React from 'react';
import { useLocation } from 'wouter';
import { Clock, ChevronRight } from 'lucide-react';
import type { RunSummary } from '../../api/types';
import { formatTime } from '../../lib/segments';

interface RecentRunsProps {
  runs: RunSummary[];
}

export const RecentRuns: React.FC<RecentRunsProps> = ({ runs }) => {
  const [, setLocation] = useLocation();

  if (!runs || runs.length === 0) return null;

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    } catch {
      return '';
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
        {runs.map((r, i) => (
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
              borderBottom: i < runs.length - 1 ? '1px solid var(--rule)' : 'none',
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
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s3)', minWidth: 0 }}>
              <Clock size={16} color="var(--ink-soft)" style={{ flexShrink: 0 }} />
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--s2)', minWidth: 0 }}>
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

            <ChevronRight size={16} color="var(--ink-soft)" style={{ flexShrink: 0 }} />
          </div>
        ))}
      </div>
    </section>
  );
};
