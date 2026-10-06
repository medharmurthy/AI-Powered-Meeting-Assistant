import React, { useState } from 'react';
import { ShieldCheck, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react';
import type { Correction } from '../../api/types';

interface ChangesSummaryProps {
  corrections: Correction[];
}

export const ChangesSummary: React.FC<ChangesSummaryProps> = ({ corrections }) => {
  const [isBlockedExpanded, setIsBlockedExpanded] = useState(false);

  if (!corrections || corrections.length === 0) return null;

  const applied = corrections.filter((c) => c.status === 'applied');
  const blocked = corrections.filter((c) => c.status === 'blocked');

  return (
    <div
      className="sheet"
      style={{
        marginTop: 'var(--s5)',
        padding: 'var(--s4)',
        background: 'var(--paper)',
        borderRadius: 'var(--r-ctl)',
        border: '1px solid var(--rule)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--s2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)' }}>
          <ShieldCheck size={18} color="var(--blue)" />
          <span style={{ fontWeight: 600, fontSize: 'var(--t-sm)', color: 'var(--ink)' }}>
            {applied.length} {applied.length === 1 ? 'correction' : 'corrections'} applied
            {blocked.length > 0 && `, ${blocked.length} blocked by safety checks`}
          </span>
        </div>

        {blocked.length > 0 && (
          <button
            type="button"
            onClick={() => setIsBlockedExpanded(!isBlockedExpanded)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'none',
              border: 'none',
              color: 'var(--ink-soft)',
              fontSize: 'var(--t-xs)',
              cursor: 'pointer',
              padding: '2px 6px',
            }}
          >
            <span>{isBlockedExpanded ? 'Hide safety checks' : 'Review blocked edits'}</span>
            {isBlockedExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>

      {/* Expandable Blocked Guardrails Review */}
      {isBlockedExpanded && blocked.length > 0 && (
        <div
          style={{
            marginTop: 'var(--s3)',
            paddingTop: 'var(--s3)',
            borderTop: '1px solid var(--rule)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--s2)',
          }}
        >
          <div style={{ fontSize: '11px', color: 'var(--ink-soft)', marginBottom: '4px' }}>
            The following candidate replacements were blocked by safety guardrails to prevent hallucination:
          </div>
          {blocked.map((b) => (
            <div
              key={b.id}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: 'var(--s2)',
                padding: '6px 10px',
                background: 'var(--sheet)',
                borderRadius: 'var(--r-ctl)',
                border: '1px solid var(--rule)',
                fontSize: 'var(--t-xs)',
              }}
            >
              <AlertCircle size={14} color="var(--alert)" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="del-mark" style={{ color: 'var(--ink-soft)' }}>{b.original}</span>
                  <span>→</span>
                  <span style={{ fontWeight: 600, color: 'var(--alert)' }}>{b.corrected}</span>
                  <span
                    className="chip-pill"
                    style={{
                      marginLeft: 'auto',
                      fontSize: '10px',
                      background: 'var(--alert-wash)',
                      color: 'var(--alert)',
                      padding: '1px 6px',
                    }}
                  >
                    Blocked
                  </span>
                </div>
                {b.block_reason && (
                  <div style={{ color: 'var(--ink-soft)', fontSize: '11px', marginTop: '2px' }}>
                    Guardrail: {b.block_reason}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
