import React, { useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import type { RunState } from '../../api/types';
import { SegmentRow } from './SegmentRow';
import { useFocusStore } from '../../state/focusStore';

interface TranscriptPaneProps {
  run: RunState;
  onSeekTime?: (time: number) => void;
}

type TabType = 'raw' | 'refined' | 'compare';

export const TranscriptPane: React.FC<TranscriptPaneProps> = ({ run, onSeekTime }) => {
  const [activeTab, setActiveTab] = useState<TabType>('raw');
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const { clearAll } = useFocusStore();

  const isStreaming = run.status === 'running' && run.stage === 'transcribe';
  const rawSegments = run.raw || [];
  const refinedSegments = run.refined || [];

  // Global keyboard shortcuts: / for search, Esc to clear, 1/2/3 for tabs
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput = activeEl instanceof HTMLInputElement || activeEl instanceof HTMLTextAreaElement;

      if (e.key === '/' && !isInput) {
        e.preventDefault();
        searchInputRef.current?.focus();
      } else if (e.key === 'Escape') {
        if (searchQuery) {
          setSearchQuery('');
        }
        clearAll();
        if (isInput) {
          (activeEl as HTMLElement).blur();
        }
      } else if (!isInput) {
        if (e.key === '1') setActiveTab('raw');
        else if (e.key === '2') setActiveTab('refined');
        else if (e.key === '3') setActiveTab('compare');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchQuery, clearAll]);

  // Auto-scroll to newest segment as lines stream in
  useEffect(() => {
    if (isStreaming && rawSegments.length > 0 && activeTab === 'raw') {
      const container = scrollContainerRef.current;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [rawSegments.length, isStreaming, activeTab]);

  const filteredRaw = searchQuery.trim()
    ? rawSegments.filter((s) => s.text.toLowerCase().includes(searchQuery.toLowerCase()))
    : rawSegments;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Tab bar & Search header */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px var(--s4)',
          borderBottom: '1px solid var(--rule)',
          background: 'var(--sheet)',
          gap: 'var(--s3)',
          flexWrap: 'wrap',
        }}
      >
        {/* Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s1)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('raw')}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--r-ctl)',
              border: 'none',
              background: activeTab === 'raw' ? 'var(--blue-wash)' : 'transparent',
              color: activeTab === 'raw' ? 'var(--blue)' : 'var(--ink-soft)',
              fontWeight: activeTab === 'raw' ? 700 : 500,
              fontSize: 'var(--t-xs)',
              cursor: 'pointer',
            }}
          >
            Raw {rawSegments.length > 0 && `(${rawSegments.length})`}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('refined')}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--r-ctl)',
              border: 'none',
              background: activeTab === 'refined' ? 'var(--blue-wash)' : 'transparent',
              color: activeTab === 'refined' ? 'var(--blue)' : 'var(--ink-soft)',
              fontWeight: activeTab === 'refined' ? 700 : 500,
              fontSize: 'var(--t-xs)',
              cursor: 'pointer',
            }}
          >
            Refined {refinedSegments.length > 0 && `(${refinedSegments.length})`}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('compare')}
            style={{
              padding: '4px 10px',
              borderRadius: 'var(--r-ctl)',
              border: 'none',
              background: activeTab === 'compare' ? 'var(--blue-wash)' : 'transparent',
              color: activeTab === 'compare' ? 'var(--blue)' : 'var(--ink-soft)',
              fontWeight: activeTab === 'compare' ? 700 : 500,
              fontSize: 'var(--t-xs)',
              cursor: 'pointer',
            }}
          >
            Compare
          </button>
        </div>

        {/* Search input with / shortcut */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '3px 8px',
            background: 'var(--paper)',
            border: '1px solid var(--rule)',
            borderRadius: 'var(--r-ctl)',
            maxWidth: '220px',
            flex: 1,
          }}
        >
          <Search size={14} color="var(--ink-soft)" style={{ flexShrink: 0 }} />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search /"
            style={{
              border: 'none',
              outline: 'none',
              background: 'transparent',
              color: 'var(--ink)',
              fontSize: 'var(--t-xs)',
              width: '100%',
            }}
          />
          {searchQuery ? (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                cursor: 'pointer',
                color: 'var(--ink-soft)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <X size={12} />
            </button>
          ) : (
            <kbd
              style={{
                fontSize: '10px',
                padding: '1px 4px',
                borderRadius: '3px',
                background: 'var(--sheet)',
                border: '1px solid var(--rule)',
                color: 'var(--ink-soft)',
                fontFamily: 'inherit',
              }}
            >
              /
            </kbd>
          )}
        </div>
      </header>

      {/* Transcript Scroll Area */}
      <div
        ref={scrollContainerRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--s3) 0',
        }}
      >
        {activeTab === 'raw' && (
          <div>
            {filteredRaw.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {filteredRaw.map((seg, idx) => (
                  <SegmentRow
                    key={seg.id}
                    segment={seg}
                    isLatest={idx === filteredRaw.length - 1}
                    isStreaming={isStreaming}
                    searchQuery={searchQuery}
                    onTimeClick={onSeekTime}
                  />
                ))}
              </div>
            ) : isStreaming ? (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                Listening for speech…
              </div>
            ) : searchQuery ? (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)' }}>
                No segments matching “{searchQuery}”
              </div>
            ) : (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                No speech detected in this recording.
              </div>
            )}
          </div>
        )}

        {activeTab === 'refined' && (
          <div style={{ padding: 'var(--s4)' }}>
            {refinedSegments.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s2)' }}>
                {refinedSegments.map((seg) => (
                  <div key={seg.id} style={{ display: 'flex', gap: 'var(--s3)', fontSize: '15px', lineHeight: 1.6 }}>
                    <span className="tabular-nums" style={{ color: 'var(--ink-soft)', width: '60px', flexShrink: 0, fontSize: 'var(--t-xs)' }}>
                      {Math.floor(seg.start / 60).toString().padStart(2, '0')}:
                      {Math.floor(seg.start % 60).toString().padStart(2, '0')}
                    </span>
                    <span className="font-doc" style={{ color: 'var(--ink)', flex: 1 }}>
                      {seg.text}
                    </span>
                  </div>
                ))}
              </div>
            ) : run.status === 'running' && run.stage === 'refine' ? (
              <div style={{ color: 'var(--blue)', fontStyle: 'italic', textAlign: 'center', padding: 'var(--s5)' }}>
                Checking terms and proper nouns…
              </div>
            ) : (
              <div style={{ color: 'var(--ink-soft)', fontStyle: 'italic', textAlign: 'center', padding: 'var(--s5)' }}>
                Refined transcript will appear after term correction completes.
              </div>
            )}
          </div>
        )}

        {activeTab === 'compare' && (
          <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontSize: 'var(--t-sm)' }}>
            {run.corrections && run.corrections.length > 0 ? (
              <div>
                <div style={{ fontWeight: 600, color: 'var(--ink)', marginBottom: 'var(--s3)' }}>
                  {run.corrections.filter((c) => c.status === 'applied').length} corrections applied,{' '}
                  {run.corrections.filter((c) => c.status === 'blocked').length} blocked by safety checks
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s2)', textAlign: 'left', maxWidth: '600px', margin: '0 auto' }}>
                  {run.corrections.map((c) => (
                    <div
                      key={c.id}
                      style={{
                        padding: '8px 12px',
                        background: 'var(--paper)',
                        border: '1px solid var(--rule)',
                        borderRadius: 'var(--r-ctl)',
                        fontSize: 'var(--t-xs)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s2)', marginBottom: '2px' }}>
                        <span className="del-mark">{c.original}</span>
                        <span>→</span>
                        <span className="ins-mark" style={{ fontWeight: 600 }}>{c.corrected}</span>
                        <span
                          className="chip-pill"
                          style={{
                            marginLeft: 'auto',
                            fontSize: '10px',
                            background: c.status === 'applied' ? 'var(--blue-wash)' : 'var(--alert-wash)',
                            color: c.status === 'applied' ? 'var(--blue)' : 'var(--alert)',
                          }}
                        >
                          {c.status}
                        </span>
                      </div>
                      <div style={{ color: 'var(--ink-soft)' }}>{c.reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p style={{ fontStyle: 'italic' }}>
                Compare view will show term corrections once refinement completes.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
