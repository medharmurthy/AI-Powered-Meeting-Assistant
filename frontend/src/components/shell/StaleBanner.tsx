import React from 'react';
import { RotateCcw } from 'lucide-react';

interface StaleBannerProps {
  onRewrite: () => void;
  isRewriting?: boolean;
}

export const StaleBanner: React.FC<StaleBannerProps> = ({ onRewrite, isRewriting }) => {
  return (
    <div className="stale-banner" role="status">
      <span>You changed the transcript. The record still reflects the earlier version.</span>
      <button
        type="button"
        className="chip-pill"
        onClick={onRewrite}
        disabled={isRewriting}
        style={{
          background: 'var(--sheet)',
          border: '1px solid var(--ink)',
          color: 'var(--ink)',
          cursor: isRewriting ? 'not-allowed' : 'pointer',
        }}
      >
        <RotateCcw size={13} />
        <span>{isRewriting ? 'Rewriting...' : 'Rewrite record'}</span>
      </button>
    </div>
  );
};
