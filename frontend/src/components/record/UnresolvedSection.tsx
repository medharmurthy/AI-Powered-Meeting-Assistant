import React from 'react';
import type { Segment, Unresolved, UnresolvedKind } from '../../api/types';
import { EvidenceChip } from './EvidenceChip';

interface UnresolvedSectionProps {
  unresolved?: Unresolved[];
  segments?: Segment[];
  isWriting?: boolean;
}

const KIND_LABELS: Record<UnresolvedKind, string> = {
  proposal: 'Proposal',
  question: 'Open question',
  deferred: 'Deferred',
  possible_task: 'Possible task',
};

export const UnresolvedSection: React.FC<UnresolvedSectionProps> = ({
  unresolved,
  segments,
  isWriting,
}) => {
  const count = unresolved?.length ?? 0;

  return (
    <section id="section-unresolved" style={{ marginBottom: 'var(--s6)' }}>
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
          Discussed, not settled
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s3)' }}>
          {unresolved!.map((item, idx) => {
            const kindLabel = KIND_LABELS[item.kind] || item.kind;
            return (
              <div
                key={item.id || idx}
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 'var(--s2)',
                  padding: '6px 0',
                  borderBottom: '1px solid var(--rule)',
                  flexWrap: 'wrap',
                }}
              >
                <span
                  className="chip-pill"
                  style={{
                    background: 'var(--paper)',
                    color: 'var(--ink-soft)',
                    border: '1px solid var(--rule)',
                    fontSize: '11px',
                    padding: '2px 8px',
                    fontWeight: 600,
                    flexShrink: 0,
                  }}
                >
                  {kindLabel}
                </span>

                <span
                  className="font-doc"
                  style={{
                    fontSize: '15px',
                    color: 'var(--ink)',
                    lineHeight: 1.5,
                    flex: 1,
                  }}
                >
                  {item.text}
                </span>

                <EvidenceChip segmentIds={item.segment_ids} segments={segments} />
              </div>
            );
          })}
        </div>
      ) : isWriting ? (
        <p style={{ color: 'var(--blue)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Checking unresolved items…
        </p>
      ) : (
        <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-sm)' }}>
          No unresolved items were identified.
        </p>
      )}
    </section>
  );
};
