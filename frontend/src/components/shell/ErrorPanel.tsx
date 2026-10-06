import React, { useState } from 'react';
import { Copy, Check, RotateCcw } from 'lucide-react';
import type { AppError } from '../../api/types';

interface ErrorPanelProps {
  error: AppError;
  onRetry?: () => void;
}

export const ErrorPanel: React.FC<ErrorPanelProps> = ({ error, onRetry }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (error.fix) {
      navigator.clipboard.writeText(error.fix);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="error-panel" role="alert">
      <div className="error-panel-title">{error.title}</div>
      <div className="error-panel-detail">{error.detail}</div>

      {error.fix && (
        <div className="error-panel-fix">
          <code>{error.fix}</code>
          <button
            type="button"
            onClick={handleCopy}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--ink-soft)',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Copy fix command"
            aria-label="Copy fix command"
          >
            {copied ? <Check size={14} color="var(--ok)" /> : <Copy size={14} />}
          </button>
        </div>
      )}

      {onRetry && (
        <div style={{ marginTop: 'var(--s2)' }}>
          <button
            type="button"
            onClick={onRetry}
            className="chip-pill"
            style={{
              background: 'var(--sheet)',
              border: '1px solid var(--alert)',
              color: 'var(--alert)',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={13} />
            <span>Retry from this step</span>
          </button>
        </div>
      )}
    </div>
  );
};
