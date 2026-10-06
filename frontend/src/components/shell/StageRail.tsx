import React from 'react';
import type { Stage } from '../../api/types';

interface StageRailProps {
  currentStage: Stage | null;
  status: 'queued' | 'running' | 'done' | 'failed';
  timings?: Partial<Record<Stage, number>>;
  progress?: Partial<Record<Stage, { done: number; total: number; label: string }>>;
  models?: { stt?: string; refiner?: string; documenter?: string };
}

export const StageRail: React.FC<StageRailProps> = ({
  currentStage,
  status,
  timings = {},
  progress = {},
  models = {},
}) => {
  const steps: { key: Stage; label: string; modelName: string; index: number }[] = [
    { key: 'transcribe', label: 'Transcribe', modelName: models.stt || 'Whisper', index: 1 },
    { key: 'refine', label: 'Correct terms', modelName: models.refiner || 'Qwen', index: 2 },
    { key: 'document', label: 'Write the record', modelName: models.documenter || 'Gemma', index: 3 },
  ];

  const getStepStatus = (key: Stage) => {
    if (status === 'failed' && currentStage === key) return 'failed';
    if (timings[key] !== undefined) return 'done';
    if (status === 'running' && currentStage === key) return 'active';
    if (status === 'done') return 'done';
    return 'waiting';
  };

  return (
    <nav className="stage-rail" aria-label="Pipeline progress">
      <div className="sr-only" aria-live="polite">
        Current stage: {currentStage || status}
      </div>

      {steps.map((step) => {
        const stepStatus = getStepStatus(step.key);
        const timing = timings[step.key];
        const stepProgress = progress[step.key];

        let secondaryLabel = step.modelName;
        if (stepStatus === 'done' && timing !== undefined) {
          secondaryLabel = `✓ ${timing}s`;
        } else if (stepStatus === 'active') {
          secondaryLabel = stepProgress?.label || '● running';
        } else if (stepStatus === 'failed') {
          secondaryLabel = 'failed';
        }

        return (
          <div
            key={step.key}
            className={`stage-step ${stepStatus}`}
            title={`${step.label} (${step.modelName})`}
          >
            <span className="stage-badge">{step.index}</span>
            <span style={{ fontWeight: 600 }}>{step.label}</span>
            <span style={{ fontSize: 'var(--t-xs)', color: 'var(--ink-soft)' }}>
              {secondaryLabel}
            </span>
          </div>
        );
      })}
    </nav>
  );
};
