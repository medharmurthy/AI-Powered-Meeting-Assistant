import React, { useEffect } from 'react';
import { useRoute } from 'wouter';
import { Topbar } from '../components/shell/Topbar';
import { StageRail } from '../components/shell/StageRail';
import { SplitPane } from '../components/shell/SplitPane';
import { ErrorPanel } from '../components/shell/ErrorPanel';
import { StaleBanner } from '../components/shell/StaleBanner';
import { useRunStore } from '../state/runStore';
import { rerunStage } from '../api/client';

export const RunView: React.FC = () => {
  const [, params] = useRoute<{ id: string }>('/r/:id');
  const runId = params?.id;
  const { currentRun, isLoading, loadRun } = useRunStore();

  useEffect(() => {
    if (runId) {
      loadRun(runId);
    }
  }, [runId, loadRun]);

  const handleRewrite = async () => {
    if (runId) {
      await rerunStage(runId, 'document');
      loadRun(runId);
    }
  };

  const handleRetryFromStep = async () => {
    if (runId && currentRun?.stage) {
      const fromStage = currentRun.stage === 'document' ? 'document' : 'refine';
      await rerunStage(runId, fromStage);
      loadRun(runId);
    }
  };

  if (!currentRun && isLoading) {
    return (
      <div className="app-container">
        <Topbar runTitle="Loading..." />
        <div style={{ padding: 'var(--s6)', textAlign: 'center', color: 'var(--ink-soft)' }}>
          Loading workspace...
        </div>
      </div>
    );
  }

  const title = currentRun?.record?.title || currentRun?.filename || 'Meeting';

  return (
    <div className="app-container">
      {currentRun?.fake && (
        <div className="demo-banner" role="banner">
          Demo data, not produced from this audio
        </div>
      )}

      <Topbar runTitle={title} />

      <StageRail
        currentStage={currentRun?.stage || null}
        status={currentRun?.status || 'queued'}
        timings={currentRun?.timings}
        progress={currentRun?.progress}
        models={currentRun?.models}
      />

      {currentRun?.recordStale && (
        <StaleBanner onRewrite={handleRewrite} />
      )}

      {currentRun?.error && (
        <ErrorPanel error={currentRun.error} onRetry={handleRetryFromStep} />
      )}

      <SplitPane
        leftPane={
          <div style={{ padding: 'var(--s5)' }}>
            <h2 style={{ fontFamily: 'var(--font-doc)', fontSize: 'var(--t-xl)', marginBottom: 'var(--s3)' }}>
              {currentRun?.record?.title || 'Meeting Record'}
            </h2>
            {currentRun?.record?.summary ? (
              <p className="font-doc" style={{ lineHeight: 1.65, color: 'var(--ink)' }}>
                {currentRun.record.summary}
              </p>
            ) : (
              <p style={{ color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                {currentRun?.status === 'running' ? 'Writing record...' : 'No record available yet.'}
              </p>
            )}
          </div>
        }
        rightPane={
          <div style={{ padding: 'var(--s5)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--s4)' }}>
              <h2 style={{ fontSize: 'var(--t-md)', fontWeight: 600 }}>Transcript</h2>
              <span style={{ fontSize: 'var(--t-xs)', color: 'var(--ink-soft)' }}>
                {currentRun?.raw?.length || 0} segments
              </span>
            </div>

            {currentRun?.raw && currentRun.raw.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s3)' }}>
                {currentRun.raw.map((seg) => (
                  <div key={seg.id} style={{ display: 'flex', gap: 'var(--s3)', fontSize: '15.5px' }}>
                    <span className="tabular-nums" style={{ color: 'var(--ink-soft)', flex: '0 0 54px' }}>
                      {Math.floor(seg.start / 60).toString().padStart(2, '0')}:
                      {Math.floor(seg.start % 60).toString().padStart(2, '0')}
                    </span>
                    <span className="font-doc" style={{ flex: 1 }}>{seg.text}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: 'var(--ink-soft)', fontStyle: 'italic' }}>
                {currentRun?.status === 'running' ? 'Listening for speech...' : 'Empty transcript.'}
              </div>
            )}
          </div>
        }
      />
    </div>
  );
};
