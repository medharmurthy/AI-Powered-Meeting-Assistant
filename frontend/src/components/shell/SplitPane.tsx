import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useUIStore } from '../../state/uiStore';

interface SplitPaneProps {
  leftPane: React.ReactNode;
  rightPane: React.ReactNode;
}

export const SplitPane: React.FC<SplitPaneProps> = ({ leftPane, rightPane }) => {
  const { splitRatio, setSplitRatio } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [activeMobilePane, setActiveMobilePane] = useState<'record' | 'transcript'>('record');
  const containerRef = useRef<HTMLDivElement>(null);

  // Monitor viewport width for <= 960px breakpoint
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(max-width: 960px)');
    setIsMobile(mediaQuery.matches);

    const handler = (e: MediaQueryListEvent) => {
      setIsMobile(e.matches);
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  const startDragging = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newRatio = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitRatio(newRatio);
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
      }
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, setSplitRatio]);

  if (isMobile) {
    return (
      <div
        className="split-pane-container mobile"
        ref={containerRef}
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        {/* Two-item switch (Record | Transcript) below 960px */}
        <div
          role="tablist"
          aria-label="Pane switch"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '8px var(--s4)',
            background: 'var(--paper)',
            borderBottom: '1px solid var(--rule)',
            flexShrink: 0,
          }}
        >
          <button
            role="tab"
            aria-selected={activeMobilePane === 'record'}
            type="button"
            onClick={() => setActiveMobilePane('record')}
            style={{
              padding: '6px 16px',
              borderRadius: 'var(--r-ctl)',
              border: '1px solid',
              borderColor: activeMobilePane === 'record' ? 'var(--blue)' : 'var(--rule)',
              background: activeMobilePane === 'record' ? 'var(--blue-wash)' : 'var(--sheet)',
              color: activeMobilePane === 'record' ? 'var(--blue)' : 'var(--ink-soft)',
              fontWeight: activeMobilePane === 'record' ? 700 : 500,
              fontSize: 'var(--t-sm)',
              cursor: 'pointer',
              flex: 1,
              maxWidth: '160px',
            }}
          >
            Record
          </button>
          <button
            role="tab"
            aria-selected={activeMobilePane === 'transcript'}
            type="button"
            onClick={() => setActiveMobilePane('transcript')}
            style={{
              padding: '6px 16px',
              borderRadius: 'var(--r-ctl)',
              border: '1px solid',
              borderColor: activeMobilePane === 'transcript' ? 'var(--blue)' : 'var(--rule)',
              background: activeMobilePane === 'transcript' ? 'var(--blue-wash)' : 'var(--sheet)',
              color: activeMobilePane === 'transcript' ? 'var(--blue)' : 'var(--ink-soft)',
              fontWeight: activeMobilePane === 'transcript' ? 700 : 500,
              fontSize: 'var(--t-sm)',
              cursor: 'pointer',
              flex: 1,
              maxWidth: '160px',
            }}
          >
            Transcript
          </button>
        </div>

        {/* Selected Pane */}
        <div
          className={activeMobilePane === 'record' ? 'split-left-pane' : 'split-right-pane'}
          style={{ flex: 1, overflowY: 'auto', width: '100%' }}
        >
          {activeMobilePane === 'record' ? leftPane : rightPane}
        </div>
      </div>
    );
  }

  return (
    <div className="split-pane-container" ref={containerRef}>
      <div
        className="split-left-pane"
        style={{ flex: `0 0 ${splitRatio}%`, width: `${splitRatio}%` }}
      >
        {leftPane}
      </div>

      <div
        className={`split-resizer ${isDragging ? 'dragging' : ''}`}
        onMouseDown={startDragging}
        role="separator"
        aria-orientation="vertical"
        aria-valuenow={Math.round(splitRatio)}
        tabIndex={0}
      />

      <div
        className="split-right-pane"
        style={{ flex: 1 }}
      >
        {rightPane}
      </div>
    </div>
  );
};
