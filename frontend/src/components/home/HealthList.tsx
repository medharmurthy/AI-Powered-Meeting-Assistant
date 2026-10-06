import React, { useState } from 'react';
import { Copy, Check, AlertTriangle } from 'lucide-react';
import type { AppError } from '../../api/types';

interface HealthListProps {
  issues: AppError[];
}

export const HealthList: React.FC<HealthListProps> = ({ issues }) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  if (!issues || issues.length === 0) return null;

  const handleCopy = (fix: string, idx: number) => {
    // Strip backticks if present
    const cleanFix = fix.replace(/^`+|`+$/g, '').trim();
    navigator.clipboard.writeText(cleanFix);
    setCopiedIndex(idx);
    setTimeout(() => {
      setCopiedIndex(null);
    }, 2000);
  };

  return (
    <div style={{ marginBottom: 'var(--s5)' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s2)' }}>
        {issues.map((issue, idx) => (
          <div
            key={`${issue.code}-${idx}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--s2) var(--s3)',
              background: 'var(--alert-wash)',
              border: '1px solid var(--alert)',
              borderRadius: 'var(--r-ctl)',
              fontSize: 'var(--t-xs)',
              gap: 'var(--s3)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)', flex: 1, minWidth: 0 }}>
              <AlertTriangle size={15} color="var(--alert)" style={{ flexShrink: 0 }} />
              <span style={{ fontWeight: 600, color: 'var(--alert)' }}>
                {issue.title}:
              </span>
              <span style={{ color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {issue.detail || issue.fix}
              </span>
            </div>

            {issue.fix && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)', flexShrink: 0 }}>
                <code
                  style={{
                    background: 'var(--sheet)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    border: '1px solid var(--rule)',
                    fontSize: '11.5px',
                    color: 'var(--ink)',
                  }}
                >
                  {issue.fix}
                </code>
                <button
                  type="button"
                  onClick={() => handleCopy(issue.fix!, idx)}
                  title="Copy command"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '2px 8px',
                    borderRadius: 'var(--r-ctl)',
                    border: '1px solid var(--rule)',
                    background: 'var(--sheet)',
                    color: 'var(--ink-soft)',
                    cursor: 'pointer',
                    fontSize: '11px',
                  }}
                >
                  {copiedIndex === idx ? (
                    <>
                      <Check size={12} color="var(--ok)" />
                      <span style={{ color: 'var(--ok)' }}>Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={12} />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
