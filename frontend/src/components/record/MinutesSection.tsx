import React from 'react';
import type { MinutesTopic, Segment } from '../../api/types';
import { EvidenceChip } from './EvidenceChip';

interface MinutesSectionProps {
  topics?: MinutesTopic[];
  segments?: Segment[];
  isWriting?: boolean;
}

export const MinutesSection: React.FC<MinutesSectionProps> = ({
  topics,
  segments,
  isWriting,
}) => {
  return (
    <section id="section-minutes" style={{ marginBottom: 'var(--s6)' }}>
      <h3
        style={{
          fontSize: 'var(--t-xs)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: 'var(--ink-soft)',
          marginBottom: 'var(--s3)',
        }}
      >
        Minutes
      </h3>

      {topics && topics.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s5)' }}>
          {topics.map((topic, tIdx) => (
            <div key={`${topic.title}-${tIdx}`}>
              <h4
                style={{
                  fontSize: 'var(--t-sm)',
                  fontWeight: 600,
                  color: 'var(--ink)',
                  marginBottom: 'var(--s2)',
                }}
              >
                {topic.title}
              </h4>
              <ul
                style={{
                  listStyle: 'disc',
                  paddingLeft: 'var(--s4)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 'var(--s2)',
                }}
              >
                {topic.points.map((pt, pIdx) => (
                  <li
                    key={pIdx}
                    className="font-doc"
                    style={{
                      fontSize: '15px',
                      lineHeight: 1.6,
                      color: 'var(--ink)',
                      maxWidth: 'var(--measure)',
                    }}
                  >
                    <span>{pt.text} </span>
                    <EvidenceChip segmentIds={pt.segment_ids} segments={segments} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : isWriting ? (
        <p style={{ color: 'var(--blue)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Writing minutes…
        </p>
      ) : (
        <p style={{ color: 'var(--ink-soft)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Waiting
        </p>
      )}
    </section>
  );
};
