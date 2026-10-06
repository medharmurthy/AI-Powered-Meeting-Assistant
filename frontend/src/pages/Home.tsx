import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { Play, UploadCloud } from 'lucide-react';
import { Topbar } from '../components/shell/Topbar';
import { createSampleRun, fetchRuns } from '../api/client';
import type { RunSummary } from '../api/types';

export const Home: React.FC = () => {
  const [, setLocation] = useLocation();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [isLoadingSample, setIsLoadingSample] = useState(false);

  useEffect(() => {
    fetchRuns().then(setRuns).catch(() => {});
  }, []);

  const handleTrySample = async () => {
    setIsLoadingSample(true);
    try {
      const { run_id } = await createSampleRun();
      setLocation(`/r/${run_id}`);
    } catch (err) {
      console.error('Failed to launch sample run', err);
    } finally {
      setIsLoadingSample(false);
    }
  };

  return (
    <div className="app-container">
      <Topbar />

      <main style={{ maxWidth: '880px', width: '100%', margin: '0 auto', padding: 'var(--s6) var(--s5)' }}>
        <section style={{ marginBottom: 'var(--s5)' }}>
          <h1 style={{ fontFamily: 'var(--font-doc)', fontSize: 'var(--t-2xl)', fontWeight: 600, marginBottom: 'var(--s2)' }}>
            Drop a meeting recording
          </h1>
          <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-md)' }}>
            Get a transcript, corrected technical terms, decisions and tasks. Each one links back to the audio.
          </p>
        </section>

        {/* Drop target card shell */}
        <div
          className="sheet"
          style={{
            padding: 'var(--s7) var(--s5)',
            textAlign: 'center',
            marginBottom: 'var(--s6)',
            cursor: 'pointer',
          }}
        >
          <UploadCloud size={40} color="var(--ink-soft)" style={{ margin: '0 auto var(--s3) auto' }} />
          <div style={{ fontSize: 'var(--t-lg)', fontWeight: 600, marginBottom: 'var(--s2)' }}>
            Drop a meeting recording or choose a file
          </div>
          <div style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>
            wav, mp3, m4a, flac, ogg, mp4 · up to 500 MB
          </div>

          <div style={{ marginTop: 'var(--s5)' }}>
            <button
              type="button"
              className="chip-pill"
              onClick={handleTrySample}
              disabled={isLoadingSample}
              style={{
                background: 'var(--blue-wash)',
                color: 'var(--blue)',
                border: '1px solid var(--blue)',
                cursor: 'pointer',
                padding: '8px 16px',
                fontSize: 'var(--t-sm)',
              }}
            >
              <Play size={14} />
              <span>{isLoadingSample ? 'Starting sample...' : 'Try the sample recording'}</span>
            </button>
          </div>
        </div>

        {/* Recent Runs list */}
        {runs.length > 0 && (
          <section>
            <h2 style={{ fontSize: 'var(--t-md)', fontWeight: 600, marginBottom: 'var(--s3)', color: 'var(--ink-soft)' }}>
              Recent recordings
            </h2>
            <div className="sheet" style={{ overflow: 'hidden' }}>
              {runs.map((r, i) => (
                <div
                  key={r.id}
                  onClick={() => setLocation(`/r/${r.id}`)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--s3) var(--s4)',
                    borderBottom: i < runs.length - 1 ? '1px solid var(--rule)' : 'none',
                    cursor: 'pointer',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{r.title || r.filename}</span>
                  <div style={{ display: 'flex', gap: 'var(--s3)', color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>
                    <span>{r.duration ? `${Math.round(r.duration)}s` : ''}</span>
                    <span style={{ textTransform: 'capitalize' }}>{r.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
};
