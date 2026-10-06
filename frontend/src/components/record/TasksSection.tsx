import React from 'react';
import type { ActionItem, Segment } from '../../api/types';
import { Unspecified } from './Unspecified';
import { EvidenceChip } from './EvidenceChip';

interface TasksSectionProps {
  actions?: ActionItem[];
  segments?: Segment[];
  isWriting?: boolean;
}

export const TasksSection: React.FC<TasksSectionProps> = ({
  actions,
  segments,
  isWriting,
}) => {
  const count = actions?.length ?? 0;

  return (
    <section id="section-tasks" style={{ marginBottom: 'var(--s6)' }}>
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
          Action items
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
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: 'var(--t-sm)',
            }}
          >
            <thead>
              <tr style={{ borderBottom: '1.5px solid var(--ink)' }}>
                <th
                  scope="col"
                  style={{
                    padding: '8px 12px 8px 0',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: 'var(--ink-soft)',
                  }}
                >
                  Task
                </th>
                <th
                  scope="col"
                  style={{
                    padding: '8px 12px',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: 'var(--ink-soft)',
                    width: '120px',
                  }}
                >
                  Owner
                </th>
                <th
                  scope="col"
                  style={{
                    padding: '8px 12px',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: 'var(--ink-soft)',
                    width: '120px',
                  }}
                >
                  Deadline
                </th>
                <th
                  scope="col"
                  style={{
                    padding: '8px 0 8px 12px',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: 'var(--ink-soft)',
                    width: '85px',
                    textAlign: 'right',
                  }}
                >
                  Source
                </th>
              </tr>
            </thead>
            <tbody>
              {actions!.map((item, idx) => (
                <tr
                  key={item.id || idx}
                  style={{
                    borderBottom: '1px solid var(--rule)',
                  }}
                >
                  <td
                    className="font-doc"
                    style={{
                      padding: '12px 12px 12px 0',
                      fontSize: '15px',
                      color: 'var(--ink)',
                      lineHeight: 1.5,
                      verticalAlign: 'top',
                    }}
                  >
                    <span>{item.task}</span>
                    {item.quote && (
                      <div
                        style={{
                          fontSize: 'var(--t-xs)',
                          color: 'var(--ink-soft)',
                          fontStyle: 'italic',
                          marginTop: '4px',
                        }}
                      >
                        “{item.quote}”
                      </div>
                    )}
                  </td>
                  <td
                    style={{
                      padding: '12px',
                      verticalAlign: 'top',
                      color: 'var(--ink)',
                    }}
                  >
                    {item.owner ? <span>{item.owner}</span> : <Unspecified />}
                  </td>
                  <td
                    style={{
                      padding: '12px',
                      verticalAlign: 'top',
                      color: 'var(--ink)',
                    }}
                  >
                    {item.deadline ? <span>{item.deadline}</span> : <Unspecified />}
                  </td>
                  <td
                    style={{
                      padding: '12px 0 12px 12px',
                      verticalAlign: 'top',
                      textAlign: 'right',
                    }}
                  >
                    <EvidenceChip segmentIds={item.segment_ids} segments={segments} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : isWriting ? (
        <p style={{ color: 'var(--blue)', fontStyle: 'italic', fontSize: 'var(--t-sm)' }}>
          Writing action items…
        </p>
      ) : (
        <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-sm)' }}>
          No tasks were assigned in this recording.
        </p>
      )}
    </section>
  );
};
