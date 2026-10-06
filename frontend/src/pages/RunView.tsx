import React, { useEffect } from 'react';
import { useRoute } from 'wouter';
import { Topbar } from '../components/shell/Topbar';
import { StageRail } from '../components/shell/StageRail';
import { SplitPane } from '../components/shell/SplitPane';
import { ErrorPanel } from '../components/shell/ErrorPanel';
import { StaleBanner } from '../components/shell/StaleBanner';
import { RecordPane } from '../components/record/RecordPane';
import { TranscriptPane } from '../components/transcript/TranscriptPane';
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
        <Topbar runTitle="Loading…" />
        <div style={{ padding: 'var(--s6)', textAlign: 'center', color: 'var(--ink-soft)' }}>
          Loading workspace…
        </div>
      </div>
    );
  }

  if (!currentRun) {
    return (
      <div className="app-container">
        <Topbar runTitle="Recording not found" />
        <div style={{ padding: 'var(--s6)', textAlign: 'center', color: 'var(--ink-soft)' }}>
          Recording not found or has been removed.
        </div>
      </div>
    );
  }

  const title = currentRun.record?.title || currentRun.filename || 'Meeting';

  return (
    <div className="app-container">
      {currentRun.fake && (
        <div className="demo-banner" role="banner">
          Demo data, not produced from this audio
        </div>
      )}

      <Topbar runTitle={title} />

      <StageRail
        currentStage={currentRun.stage}
        status={currentRun.status}
        timings={currentRun.timings}
        progress={currentRun.progress}
        models={currentRun.models}
      />

      {currentRun.recordStale && (
        <StaleBanner onRewrite={handleRewrite} />
      )}

      {currentRun.error && (
        <ErrorPanel error={currentRun.error} onRetry={handleRetryFromStep} />
      )}

      <SplitPane
        leftPane={<RecordPane run={currentRun} />}
        rightPane={<TranscriptPane run={currentRun} />}
      />
    </div>
  );
};
