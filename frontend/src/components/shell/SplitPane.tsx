import React, { useRef, useState, useCallback, useEffect } from 'react';
import { useUIStore } from '../../state/uiStore';

interface SplitPaneProps {
  leftPane: React.ReactNode;
  rightPane: React.ReactNode;
}

export const SplitPane: React.FC<SplitPaneProps> = ({ leftPane, rightPane }) => {
  const { splitRatio, setSplitRatio } = useUIStore();
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

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
