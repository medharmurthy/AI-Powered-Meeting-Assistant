import React, { useEffect, useRef } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';
import { Play, Pause, RotateCcw, RotateCw } from 'lucide-react';
import { usePlayerStore } from '../../state/playerStore';
import { useUIStore } from '../../state/uiStore';
import { formatTime } from '../../lib/segments';
import type { Segment } from '../../api/types';

interface PlayerDockProps {
  audioUrl?: string;
  peaks?: number[];
  duration?: number;
  segments?: Segment[];
}

const SPEED_OPTIONS = [0.75, 1.0, 1.25, 1.5];

function getComputedColor(varName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback;
  const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return val || fallback;
}

export const PlayerDock: React.FC<PlayerDockProps> = ({
  audioUrl,
  peaks,
  duration = 0,
  segments = [],
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const wavesurferRef = useRef<WaveSurfer | null>(null);
  const regionsPluginRef = useRef<any>(null);
  const rangeStopListenerRef = useRef<(() => void) | null>(null);

  const { theme } = useUIStore();
  const {
    time,
    playing,
    rate,
    activeRegion,
    followPlayback,
    registerController,
    unregisterController,
    setTime,
    setPlaying,
    setDuration,
    setRate,
    setFollowPlayback,
    setActiveRegion,
  } = usePlayerStore();

  // Initialize WaveSurfer instance and re-create on theme changes
  useEffect(() => {
    if (!containerRef.current || !audioUrl) return;

    // Clean up any existing instance
    if (wavesurferRef.current) {
      try {
        wavesurferRef.current.destroy();
      } catch {
        // ignore
      }
      wavesurferRef.current = null;
    }

    const waveColor = getComputedColor('--ink-soft', '#55646F');
    const progressColor = getComputedColor('--blue', '#2A44D4');
    const cursorColor = getComputedColor('--ink', '#16222B');

    let regions: any = null;
    try {
      regions = RegionsPlugin.create();
      regionsPluginRef.current = regions;
    } catch {
      // RegionsPlugin fallback
    }

    try {
      const ws = WaveSurfer.create({
        container: containerRef.current,
        url: audioUrl,
        peaks: peaks && peaks.length > 0 ? [peaks] : undefined,
        duration: duration > 0 ? duration : undefined,
        height: 56,
        barWidth: 2,
        barGap: 1,
        barRadius: 1,
        normalize: true,
        waveColor,
        progressColor,
        cursorColor,
        plugins: regions ? [regions] : [],
      });

      wavesurferRef.current = ws;

      ws.on('ready', () => {
        const dur = ws.getDuration();
        if (dur > 0) setDuration(dur);
      });

      ws.on('timeupdate', (t) => {
        setTime(t);
      });

      ws.on('play', () => setPlaying(true));
      ws.on('pause', () => setPlaying(false));
      ws.on('finish', () => setPlaying(false));

      // Register controllers for external store callers
      registerController({
        seek: (targetTime: number) => {
          try {
            const total = ws.getDuration() || duration;
            if (total > 0) {
              ws.setTime(targetTime);
            }
          } catch {
            // ignore
          }
        },
        toggle: () => {
          try {
            ws.playPause();
          } catch {
            // ignore
          }
        },
        setRate: (newRate: number) => {
          try {
            ws.setPlaybackRate(newRate);
          } catch {
            // ignore
          }
        },
        playRange: (start: number, end: number) => {
          try {
            if (rangeStopListenerRef.current) {
              rangeStopListenerRef.current();
              rangeStopListenerRef.current = null;
            }

            if (regionsPluginRef.current) {
              regionsPluginRef.current.clearRegions();
              regionsPluginRef.current.addRegion({
                id: 'evidence-range',
                start,
                end,
                color: 'rgba(255, 216, 74, 0.35)',
                drag: false,
                resize: false,
              });
            }

            ws.setTime(start);
            ws.play();

            const onTimeUpdate = (currentTime: number) => {
              if (currentTime >= end) {
                ws.pause();
                ws.un('timeupdate', onTimeUpdate);
                rangeStopListenerRef.current = null;
              }
            };

            ws.on('timeupdate', onTimeUpdate);
            rangeStopListenerRef.current = () => {
              ws.un('timeupdate', onTimeUpdate);
            };
          } catch {
            // ignore
          }
        },
      });
    } catch (err) {
      console.warn('WaveSurfer creation failed:', err);
    }

    return () => {
      unregisterController();
      if (wavesurferRef.current) {
        try {
          wavesurferRef.current.destroy();
        } catch {
          // ignore
        }
        wavesurferRef.current = null;
      }
    };
  }, [audioUrl, peaks, duration, theme, registerController, unregisterController, setTime, setPlaying, setDuration]);

  const handleTogglePlay = () => {
    wavesurferRef.current?.playPause();
  };

  const handleSeekDelta = (deltaSec: number) => {
    if (!wavesurferRef.current) return;
    const current = wavesurferRef.current.getCurrentTime();
    const target = Math.max(0, Math.min(duration || 1000, current + deltaSec));
    wavesurferRef.current.setTime(target);
  };

  const handleSpeedChange = (newRate: number) => {
    setRate(newRate);
    wavesurferRef.current?.setPlaybackRate(newRate);
  };

  const totalDuration = duration || (wavesurferRef.current?.getDuration() ?? 0);

  return (
    <footer className="player-dock" role="region" aria-label="Audio player">
      {/* Controls */}
      <div className="player-controls">
        <button
          type="button"
          onClick={handleTogglePlay}
          className="player-btn-primary"
          aria-label={playing ? 'Pause' : 'Play'}
          title={playing ? 'Pause (Space)' : 'Play (Space)'}
        >
          {playing ? <Pause size={18} /> : <Play size={18} style={{ marginLeft: '2px' }} />}
        </button>

        <button
          type="button"
          onClick={() => handleSeekDelta(-5)}
          className="player-btn"
          aria-label="Back 5 seconds"
          title="Back 5 seconds (←)"
        >
          <RotateCcw size={15} />
        </button>

        <button
          type="button"
          onClick={() => handleSeekDelta(5)}
          className="player-btn"
          aria-label="Forward 5 seconds"
          title="Forward 5 seconds (→)"
        >
          <RotateCw size={15} />
        </button>

        <div
          className="tabular-nums"
          style={{
            fontSize: 'var(--t-xs)',
            fontWeight: 600,
            color: 'var(--ink)',
            marginLeft: '4px',
            minWidth: '95px',
          }}
        >
          <span>{formatTime(time)}</span>
          <span style={{ color: 'var(--ink-soft)', margin: '0 4px' }}>/</span>
          <span style={{ color: 'var(--ink-soft)' }}>{formatTime(totalDuration)}</span>
        </div>
      </div>

      {/* Waveform with Segment Ticks Layer */}
      <div className="player-waveform-container">
        <div ref={containerRef} style={{ width: '100%', height: '56px' }} />

        {/* Segment Ticks */}
        {totalDuration > 0 && segments.length > 0 && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              pointerEvents: 'none',
              overflow: 'hidden',
            }}
            aria-hidden="true"
          >
            {segments.map((seg) => {
              const leftPercent = Math.min(100, Math.max(0, (seg.start / totalDuration) * 100));
              return (
                <div
                  key={seg.id}
                  style={{
                    position: 'absolute',
                    left: `${leftPercent}%`,
                    top: '2px',
                    width: '1px',
                    height: '10px',
                    backgroundColor: 'var(--ink-soft)',
                    opacity: 0.35,
                  }}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Trailing Controls: Evidence Indicator, Speed, Follow Playback */}
      <div className="player-trailing-controls" style={{ display: 'flex', alignItems: 'center', gap: 'var(--s3)', flexShrink: 0 }}>
        {activeRegion && (
          <div
            style={{
              fontSize: '11.5px',
              color: '#854D0E',
              backgroundColor: 'var(--marker-wash)',
              border: '1px solid var(--marker)',
              padding: '2px 8px',
              borderRadius: 'var(--r-chip)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: 'var(--marker)',
              }}
            />
            <span>yellow range = evidence</span>
            <button
              type="button"
              onClick={() => {
                setActiveRegion(null);
                regionsPluginRef.current?.clearRegions();
              }}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--ink-soft)',
                fontSize: '11px',
                padding: '0 2px',
              }}
              aria-label="Clear evidence region"
            >
              ×
            </button>
          </div>
        )}

        {/* Speed Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
          {SPEED_OPTIONS.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => handleSpeedChange(opt)}
              style={{
                background: rate === opt ? 'var(--blue-wash)' : 'transparent',
                border: 'none',
                color: rate === opt ? 'var(--blue)' : 'var(--ink-soft)',
                fontWeight: rate === opt ? 700 : 500,
                fontSize: '11.5px',
                padding: '2px 6px',
                borderRadius: 'var(--r-ctl)',
                cursor: 'pointer',
              }}
            >
              {opt}×
            </button>
          ))}
        </div>

        {/* Follow Playback Toggle */}
        <button
          type="button"
          onClick={() => setFollowPlayback(!followPlayback)}
          title="Auto-scroll transcript with audio playback"
          style={{
            padding: '4px 8px',
            borderRadius: 'var(--r-ctl)',
            border: '1px solid var(--rule)',
            background: followPlayback ? 'var(--blue-wash)' : 'transparent',
            color: followPlayback ? 'var(--blue)' : 'var(--ink-soft)',
            fontSize: '11.5px',
            fontWeight: 600,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
          }}
        >
          {followPlayback ? 'Following' : 'Follow'}
        </button>
      </div>
    </footer>
  );
};
