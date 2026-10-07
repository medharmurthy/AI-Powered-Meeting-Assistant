import React, { useState } from 'react';
import { AlertCircle, X } from 'lucide-react';
import type { AppError } from '../../api/types';

interface WarningBannerProps {
  warnings: AppError[];
}

export const WarningBanner: React.FC<WarningBannerProps> = ({ warnings }) => {
  const [dismissedCodes, setDismissedCodes] = useState<Record<string, boolean>>({});

  if (!warnings || warnings.length === 0) return null;

  const activeWarnings = warnings.filter((w) => !dismissedCodes[w.code]);
  if (activeWarnings.length === 0) return null;

  const handleDismiss = (code: string) => {
    setDismissedCodes((prev) => ({ ...prev, [code]: true }));
  };

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        padding: '6px var(--s5)',
        background: 'var(--alert-wash)',
        borderBottom: '1px solid var(--alert)',
        color: 'var(--ink)',
        fontSize: 'var(--t-xs)',
      }}
    >
      {activeWarnings.map((w) => (
        <div
          key={w.code}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 'var(--s2)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <AlertCircle size={14} color="var(--alert)" style={{ flexShrink: 0 }} />
            <span style={{ fontWeight: 600, color: 'var(--alert)' }}>
              {w.title}:
            </span>
            <span style={{ color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {w.detail || w.fix}
            </span>
          </div>

          <button
            type="button"
            onClick={() => handleDismiss(w.code)}
            title="Dismiss warning"
            aria-label="Dismiss warning"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--ink-soft)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '2px 4px',
              borderRadius: 'var(--r-ctl)',
              flexShrink: 0,
            }}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
};
