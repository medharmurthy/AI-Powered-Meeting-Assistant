import React from 'react';
import type { Decision, Segment } from '../../api/types';
import { EvidenceChip } from './EvidenceChip';

interface DecisionsSectionProps {
  decisions?: Decision[];
  segments?: Segment[];
  isWriting?: boolean;
}

export const DecisionsSection: React.FC<DecisionsSectionProps> = ({
  decisions,
  segments,
  isWriting,
}) => {
  const count = decisions?.length ?? 0;

  return (
    <section id="section-decisions" style={{ marginBottom: 'var(--s6)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)', marginBottom: 'var(--s3)' }}>
        <h3
          style={{
            fontSize: 'var(--t-xs)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--ink-soft)',
          }}
        >
          Decisions
        </h3>
        {count > 0 && (
          <span
            className="chip-pill tabular-nums"
            style={{
              background: 'var(--paper)',
              color: 'var(--ink-soft)',
              border: '1px solid var(--rule)',
              fontSize: '11px',
              padding: '1px 6px',
            }}
          >
            {count}
          </span>
        )}
      </div>

      {count > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s4)' }}>
          {decisions!.map((d, idx) => {
            const prefix = d.id.startsWith('D') ? d.id : `D${idx + 1}`;
            return (
              <div
                key={d.id || idx}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  paddingLeft: 'var(--s3)',
                  borderLeft: '2px solid var(--rule)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--s2)', flexWrap: 'wrap' }}>
                  <span style={{ fontWeight: 700, fontSize: 'var(--t-sm)', color: 'var(--ink)' }}>
                    {prefix}.
                  </span>
                  <span
                    className="font-doc"
                    style={{
                      fontSize: '16px',
                      lineHeight: 1.5,
                      fontWeight: 500,
                      color: 'var(--ink)',
                      flex: 1,
                    }}
                  >
                    {d.text}
                  </span>
                  <EvidenceChip segmentIds={d.segment_ids} segments={segments} />
                </div>

                {d.rationale && (
                  <div
                    style={{
                      fontSize: 'var(--t-xs)',
                      color: 'var(--ink-soft)',
                      paddingLeft: 'var(--s4)',
                      lineHeight: 1.4,
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>Rationale: </span>
                    {d.rationale}
                  </div>
                )}

                {d.quote && (
                  <div
                    style={{
                      fontSize: 'var(--t-xs)',
                      color: 'var(--ink-soft)',
                      fontStyle: 'italic',
                      paddingLeft: 'var(--s4)',
                    }}
                  >
                    “{d.quote}”
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : isWriting ? (
        <p style={{ color: 'var(--blue)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Writing decisions…
        </p>
      ) : (
        <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-sm)' }}>
          No decisions were agreed in this recording.
        </p>
      )}
    </section>
  );
};
