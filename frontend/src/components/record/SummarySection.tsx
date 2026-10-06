import React from 'react';

interface SummarySectionProps {
  summary?: string;
  attendees?: string[];
  isWriting?: boolean;
}

export const SummarySection: React.FC<SummarySectionProps> = ({
  summary,
  attendees,
  isWriting,
}) => {
  return (
    <section id="section-summary" style={{ marginBottom: 'var(--s6)' }}>
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
        Summary
      </h3>

      {attendees && attendees.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--s1)', marginBottom: 'var(--s3)' }}>
          <span style={{ fontSize: 'var(--t-xs)', color: 'var(--ink-soft)', alignSelf: 'center', marginRight: '4px' }}>
            Attendees:
          </span>
          {attendees.map((person, idx) => (
            <span
              key={`${person}-${idx}`}
              className="chip-pill"
              style={{
                background: 'var(--paper)',
                color: 'var(--ink)',
                border: '1px solid var(--rule)',
                fontSize: '11.5px',
                padding: '2px 8px',
              }}
            >
              {person}
            </span>
          ))}
        </div>
      )}

      {summary ? (
        <p
          className="font-doc"
          style={{
            fontSize: 'var(--t-md)',
            lineHeight: 1.65,
            color: 'var(--ink)',
            maxWidth: 'var(--measure)',
          }}
        >
          {summary}
        </p>
      ) : isWriting ? (
        <p style={{ color: 'var(--blue)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Writing summary…
        </p>
      ) : (
        <p style={{ color: 'var(--ink-soft)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Waiting
        </p>
      )}
    </section>
  );
};
