import React, { useEffect, useRef, useState } from 'react';
import { Search, X, Compass } from 'lucide-react';
import type { RunState } from '../../api/types';
import { SegmentRow } from './SegmentRow';
import { CompareRow, CollapsedUnchanged } from './CompareRow';
import { ChangesSummary } from './ChangesSummary';
import { useFocusStore } from '../../state/focusStore';
import { usePlayerStore } from '../../state/playerStore';

interface TranscriptPaneProps {
  run: RunState;
  onSeekTime?: (time: number) => void;
}

type TabType = 'raw' | 'refined' | 'compare';

export const TranscriptPane: React.FC<TranscriptPaneProps> = ({ run, onSeekTime }) => {
  const [activeTab, setActiveTab] = useState<TabType>('raw');
  const [searchQuery, setSearchQuery] = useState('');
  const [showJumpToPlayback, setShowJumpToPlayback] = useState(false);

  const searchInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isUserScrollingRef = useRef(false);

  const { clearAll } = useFocusStore();
  const {
    time: currentTime,
    duration: totalDuration,
    playing,
    followPlayback,
    setFollowPlayback,
    seek,
    toggle,
  } = usePlayerStore();

  const isStreaming = run.status === 'running' && run.stage === 'transcribe';
  const rawSegments = run.raw || [];
  const refinedSegments = run.refined || [];

  // Global keyboard shortcuts (Section 8.6)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInput =
        activeEl instanceof HTMLInputElement ||
        activeEl instanceof HTMLTextAreaElement ||
        (activeEl as HTMLElement)?.isContentEditable;

      if (e.key === '/' && !isInput) {
        e.preventDefault();
        searchInputRef.current?.focus();
        return;
      }

      if (e.key === 'Escape') {
        if (searchQuery) setSearchQuery('');
        clearAll();
        if (isInput) (activeEl as HTMLElement).blur();
        return;
      }

      if (isInput) return;

      if (e.key === ' ') {
        e.preventDefault();
        toggle();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        seek(Math.max(0, currentTime - 5));
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        seek(Math.min(totalDuration || 1000, currentTime + 5));
      } else if (e.key === 'j' || e.key === 'J') {
        // Next segment
        e.preventDefault();
        const curIdx = rawSegments.findIndex((s) => currentTime >= s.start && currentTime <= s.end);
        const nextIdx = curIdx + 1;
        if (nextIdx < rawSegments.length) {
          seek(rawSegments[nextIdx].start);
        }
      } else if (e.key === 'k' || e.key === 'K') {
        // Previous segment
        e.preventDefault();
        const curIdx = rawSegments.findIndex((s) => currentTime >= s.start && currentTime <= s.end);
        const prevIdx = curIdx > 0 ? curIdx - 1 : 0;
        if (rawSegments[prevIdx]) {
          seek(rawSegments[prevIdx].start);
        }
      } else if (e.key === '1') {
        setActiveTab('raw');
      } else if (e.key === '2') {
        setActiveTab('refined');
      } else if (e.key === '3') {
        setActiveTab('compare');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTime, totalDuration, rawSegments, searchQuery, clearAll, seek, toggle]);

  // Active Line Follow
  useEffect(() => {
    if (!followPlayback || isUserScrollingRef.current) return;

    const activeSeg = rawSegments.find((s) => currentTime >= s.start && currentTime <= s.end);
    if (activeSeg) {
      const el = document.getElementById(`seg-${activeSeg.id}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        setShowJumpToPlayback(false);
      }
    }
  }, [currentTime, followPlayback, rawSegments]);

  // Streaming auto-scroll to latest segment
  useEffect(() => {
    if (isStreaming && rawSegments.length > 0 && activeTab === 'raw') {
      const container = scrollContainerRef.current;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [rawSegments.length, isStreaming, activeTab]);

  // Detect manual scrolling to pause follow
  const handleScroll = () => {
    if (!followPlayback) return;
    const activeSeg = rawSegments.find((s) => currentTime >= s.start && currentTime <= s.end);
    if (!activeSeg) return;

    const el = document.getElementById(`seg-${activeSeg.id}`);
    const container = scrollContainerRef.current;
    if (el && container) {
      const elRect = el.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      const isVisible =
        elRect.top >= containerRect.top && elRect.bottom <= containerRect.bottom;
      if (!isVisible && playing) {
        setShowJumpToPlayback(true);
      } else {
        setShowJumpToPlayback(false);
      }
    }
  };

  const handleJumpToPlayback = () => {
    setFollowPlayback(true);
    setShowJumpToPlayback(false);
    isUserScrollingRef.current = false;
    const activeSeg = rawSegments.find((s) => currentTime >= s.start && currentTime <= s.end);
    if (activeSeg) {
      const el = document.getElementById(`seg-${activeSeg.id}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const filteredRaw = searchQuery.trim()
    ? rawSegments.filter((s) => s.text.toLowerCase().includes(searchQuery.toLowerCase()))
    : rawSegments;

  const filteredRefined = searchQuery.trim()
    ? refinedSegments.filter((s) => s.text.toLowerCase().includes(searchQuery.toLowerCase()))
    : refinedSegments;

  // Build Compare view rows with collapsed unchanged sections
  const renderCompareRows = () => {
    const rows: React.ReactNode[] = [];
    let currentUnchanged: { raw: typeof rawSegments[0]; refined: typeof refinedSegments[0] }[] = [];

    rawSegments.forEach((raw) => {
      const refined = refinedSegments.find((s) => s.id === raw.id) || { ...raw, spans: [] };
      const isModified =
        raw.text !== refined.text || (refined.spans && refined.spans.length > 0);

      if (!isModified) {
        currentUnchanged.push({ raw, refined });
      } else {
        if (currentUnchanged.length > 0) {
          if (currentUnchanged.length >= 3) {
            rows.push(
              <CollapsedUnchanged
                key={`collapsed-${currentUnchanged[0].raw.id}`}
                count={currentUnchanged.length}
                segments={currentUnchanged}
                onTimeClick={onSeekTime}
              />
            );
          } else {
            currentUnchanged.forEach(({ raw: r, refined: ref }) => {
              rows.push(
                <CompareRow
                  key={r.id}
                  segmentId={r.id}
                  rawText={r.text}
                  refinedText={ref.text}
                  start={r.start}
                  isModified={false}
                  onTimeClick={onSeekTime}
                />
              );
            });
          }
          currentUnchanged = [];
        }

        rows.push(
          <CompareRow
            key={raw.id}
            segmentId={raw.id}
            rawText={raw.text}
            refinedText={refined.text}
            start={raw.start}
            isModified={true}
            onTimeClick={onSeekTime}
          />
        );
      }
    });

    if (currentUnchanged.length > 0) {
      if (currentUnchanged.length >= 3) {
        rows.push(
          <CollapsedUnchanged
            key={`collapsed-${currentUnchanged[0].raw.id}`}
            count={currentUnchanged.length}
            segments={currentUnchanged}
            onTimeClick={onSeekTime}
          />
        );
      } else {
        currentUnchanged.forEach(({ raw: r, refined: ref }) => {
          rows.push(
            <CompareRow
              key={r.id}
              segmentId={r.id}
              rawText={r.text}
              refinedText={ref.text}
              start={r.start}
              isModified={false}
              onTimeClick={onSeekTime}
            />
          );
        });
      }
    }

    return rows;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {/* Tab bar & Search Header */}
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
              aria-label="Clear search"
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

      {/* Floating "Jump to playback" pill button */}
      {showJumpToPlayback && (
        <div
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 30,
          }}
        >
          <button
            type="button"
            onClick={handleJumpToPlayback}
            className="chip-pill"
            style={{
              background: 'var(--blue)',
              color: '#FFFFFF',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.18)',
              padding: '6px 14px',
              cursor: 'pointer',
              border: 'none',
            }}
          >
            <Compass size={14} />
            <span>Jump to playback</span>
          </button>
        </div>
      )}

      {/* Transcript Scroll Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
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
            ) : run.status === 'queued' ? (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                Queued for processing…
              </div>
            ) : run.status === 'running' ? (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                Preparing audio…
              </div>
            ) : run.status === 'failed' ? (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                Processing stopped due to an error.
              </div>
            ) : (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                No speech detected in this recording.
              </div>
            )}
          </div>
        )}

        {activeTab === 'refined' && (
          <div>
            {filteredRefined.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {filteredRefined.map((seg) => (
                  <SegmentRow
                    key={seg.id}
                    segment={seg}
                    spans={seg.spans}
                    corrections={run.corrections}
                    runId={run.id}
                    searchQuery={searchQuery}
                    onTimeClick={onSeekTime}
                  />
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
          <div style={{ padding: 'var(--s3)' }}>
            {rawSegments.length > 0 && refinedSegments.length > 0 ? (
              <div>
                {/* Column Headers */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '4px 12px',
                    borderBottom: '2px solid var(--rule)',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--ink-soft)',
                  }}
                >
                  <span style={{ width: '60px' }}>Time</span>
                  <span style={{ flex: 1, paddingRight: 'var(--s3)' }}>Raw (ASR)</span>
                  <span style={{ flex: 1, paddingLeft: 'var(--s3)' }}>Refined (Corrected)</span>
                </div>

                {/* Compare Rows */}
                {renderCompareRows()}

                {/* Changes Summary and Guardrails */}
                <ChangesSummary corrections={run.corrections || []} />
              </div>
            ) : (
              <div style={{ padding: 'var(--s5)', textAlign: 'center', color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                Compare view will show term corrections once refinement completes.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
