import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { Play, ArrowRight, Loader2 } from 'lucide-react';
import { Topbar } from '../components/shell/Topbar';
import { DropStage } from '../components/home/DropStage';
import { ChipInput } from '../components/home/ChipInput';
import { HealthList } from '../components/home/HealthList';
import { RecentRuns } from '../components/home/RecentRuns';
import { createRun, createSampleRun, fetchHealth, fetchRuns } from '../api/client';
import type { AppError, RunSummary } from '../api/types';

export const Home: React.FC = () => {
  const [, setLocation] = useLocation();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [duration, setDuration] = useState<number | null>(null);
  const [validationError, setValidationError] = useState<AppError | null>(null);

  const [glossary, setGlossary] = useState<string[]>([]);
  const [participants, setParticipants] = useState<string[]>([]);

  const [healthIssues, setHealthIssues] = useState<AppError[]>([]);
  const [runs, setRuns] = useState<RunSummary[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingSample, setIsLoadingSample] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((data) => setHealthIssues(data.issues || []))
      .catch(() => {});

    fetchRuns()
      .then(setRuns)
      .catch(() => {});
  }, []);

  const handleProcessRecording = async () => {
    if (!selectedFile || isSubmitting) return;
    setIsSubmitting(true);

    try {
      const { run_id } = await createRun(
        selectedFile,
        glossary.length > 0 ? glossary : undefined,
        participants.length > 0 ? participants : undefined
      );
      setLocation(`/r/${run_id}`);
    } catch (err: any) {
      console.error('Failed to create run', err);
      const appErr: AppError = err?.code
        ? err
        : {
            code: 'INTERNAL',
            title: 'Something went wrong',
            detail: err?.message || 'Failed to upload audio recording',
            fix: 'Check server logs and try again',
            retryable: false,
          };
      setValidationError(appErr);
      setIsSubmitting(false);
    }
  };

  const handleTrySample = async () => {
    if (isLoadingSample) return;
    setIsLoadingSample(true);
    try {
      const { run_id } = await createSampleRun();
      setLocation(`/r/${run_id}`);
    } catch (err) {
      console.error('Failed to launch sample run', err);
      setIsLoadingSample(false);
    }
  };

  return (
    <div className="app-container">
      <Topbar />

      <main
        style={{
          maxWidth: '880px',
          width: '100%',
          margin: '0 auto',
          padding: 'var(--s6) var(--s5) var(--s7) var(--s5)',
        }}
      >
        <section style={{ marginBottom: 'var(--s5)' }}>
          <h1
            style={{
              fontFamily: 'var(--font-doc)',
              fontSize: 'var(--t-2xl)',
              fontWeight: 600,
              color: 'var(--ink)',
              marginBottom: 'var(--s2)',
              letterSpacing: '-0.02em',
            }}
          >
            Drop a meeting recording
          </h1>
          <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-md)' }}>
            Get a transcript, corrected technical terms, decisions and tasks. Each one links back to the audio.
          </p>
        </section>

        {/* Drop Stage */}
        <DropStage
          selectedFile={selectedFile}
          duration={duration}
          onFileSelect={(file, dur) => {
            setSelectedFile(file);
            setDuration(dur ?? null);
          }}
          validationError={validationError}
          setValidationError={setValidationError}
        />

        {/* Actionable Health Issues if any */}
        <HealthList issues={healthIssues} />

        {/* Optional Metadata Chips */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s4)', marginBottom: 'var(--s5)' }}>
          <ChipInput
            label="Terms to listen for (optional)"
            placeholder="e.g. Kubernetes, OAuth, Redis (press Enter or comma)"
            chips={glossary}
            onChange={setGlossary}
          />

          <ChipInput
            label="Who's in the meeting (optional)"
            placeholder="e.g. Priya, Dan, Maya (press Enter or comma)"
            chips={participants}
            onChange={setParticipants}
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s4)', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleProcessRecording}
            disabled={!selectedFile || isSubmitting}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--s2)',
              padding: '10px 22px',
              borderRadius: 'var(--r-ctl)',
              background: !selectedFile || isSubmitting ? 'var(--rule)' : 'var(--blue)',
              color: !selectedFile || isSubmitting ? 'var(--ink-soft)' : '#FFFFFF',
              border: 'none',
              fontWeight: 600,
              fontSize: 'var(--t-sm)',
              cursor: !selectedFile || isSubmitting ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.15s ease',
            }}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={16} className="spin" />
                <span>Processing recording…</span>
              </>
            ) : (
              <>
                <span>Process recording</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>

          <button
            type="button"
            onClick={handleTrySample}
            disabled={isLoadingSample}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--s2)',
              padding: '10px 18px',
              borderRadius: 'var(--r-ctl)',
              background: 'transparent',
              color: 'var(--blue)',
              border: '1px solid var(--blue)',
              fontWeight: 600,
              fontSize: 'var(--t-sm)',
              cursor: isLoadingSample ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Play size={14} />
            <span>{isLoadingSample ? 'Starting sample…' : 'Try the sample recording'}</span>
          </button>
        </div>

        {/* Past Recordings */}
        <RecentRuns
          runs={runs}
          onDeleted={(id) => setRuns((prev) => prev.filter((r) => r.id !== id))}
        />
      </main>
    </div>
  );
};
