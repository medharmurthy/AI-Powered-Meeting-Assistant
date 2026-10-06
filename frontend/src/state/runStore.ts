import { create } from 'zustand';
import type { RunEvent, RunState, Stage } from '../api/types';
import { fetchRun } from '../api/client';
import { subscribeToRunEvents } from '../api/events';

export const initialRunState: RunState = {
  id: '',
  filename: '',
  status: 'queued',
  stage: null,
  models: {},
  timings: {},
  progress: {},
  raw: [],
  refined: null,
  corrections: [],
  record: {},
  recordStale: false,
  warnings: [],
};

export function applyEvent(state: RunState, event: RunEvent): RunState {
  const { type, data } = event;

  switch (type) {
    case 'run.queued':
      return {
        ...state,
        status: 'queued',
        queuePosition: data.position,
      };

    case 'run.started':
      return {
        ...state,
        status: 'running',
        models: { ...state.models, ...data.models },
      };

    case 'stage.started':
      return {
        ...state,
        stage: data.stage as Stage,
      };

    case 'stage.progress':
      return {
        ...state,
        progress: {
          ...state.progress,
          [data.stage]: data,
        },
      };

    case 'stage.done':
      return {
        ...state,
        timings: {
          ...state.timings,
          [data.stage]: data.seconds,
        },
      };

    case 'audio.ready':
      return {
        ...state,
        duration: data.duration,
        audioUrl: data.audio_url,
      };

    case 'transcript.segment': {
      const exists = state.raw.some((s) => s.id === data.id);
      const newRaw = exists
        ? state.raw.map((s) => (s.id === data.id ? data : s))
        : [...state.raw, data].sort((a, b) => a.id - b.id);
      return {
        ...state,
        raw: newRaw,
      };
    }

    case 'refine.profile':
      return {
        ...state,
        profile: data,
      };

    case 'refine.correction': {
      const exists = state.corrections.some((c) => c.id === data.id);
      const newCorrections = exists
        ? state.corrections.map((c) => (c.id === data.id ? data : c))
        : [...state.corrections, data];
      return {
        ...state,
        corrections: newCorrections,
      };
    }

    case 'refine.blocked': {
      const exists = state.corrections.some((c) => c.id === data.id);
      const newCorrections = exists
        ? state.corrections.map((c) => (c.id === data.id ? data : c))
        : [...state.corrections, data];
      return {
        ...state,
        corrections: newCorrections,
      };
    }

    case 'refine.done':
      return {
        ...state,
        refined: data.segments,
        corrections: data.corrections || state.corrections,
      };

    case 'record.section': {
      const { section, data: sectionData } = data;
      const updatedRecord = { ...state.record };

      if (section === 'summary') {
        updatedRecord.title = sectionData.title;
        updatedRecord.summary = sectionData.summary;
        updatedRecord.attendees = sectionData.attendees;
      } else if (section === 'minutes') {
        updatedRecord.minutes = sectionData.topics;
      } else if (section === 'decisions') {
        updatedRecord.decisions = sectionData.decisions;
        updatedRecord.unresolved = sectionData.unresolved;
      } else if (section === 'actions') {
        updatedRecord.action_items = sectionData.action_items;
      }

      return {
        ...state,
        record: updatedRecord,
      };
    }

    case 'warning':
      return {
        ...state,
        warnings: [...state.warnings, data],
      };

    case 'run.done':
      return {
        ...state,
        status: 'done',
        stage: null,
      };

    case 'run.failed':
      return {
        ...state,
        status: 'failed',
        error: data,
      };

    default:
      return state;
  }
}

interface RunStoreState {
  currentRun: RunState | null;
  isLoading: boolean;
  activeUnsubscribe: (() => void) | null;
  loadRun: (runId: string) => Promise<void>;
  applyLiveEvent: (event: RunEvent) => void;
  reset: () => void;
}

export const useRunStore = create<RunStoreState>((set, get) => ({
  currentRun: null,
  isLoading: false,
  activeUnsubscribe: null,

  loadRun: async (runId: string) => {
    // Unsubscribe from any previous SSE listener
    get().activeUnsubscribe?.();
    set({ isLoading: true, activeUnsubscribe: null });

    try {
      const initial = await fetchRun(runId);
      set({ currentRun: initial, isLoading: false });

      if (initial.status === 'queued' || initial.status === 'running') {
        const unsubscribe = subscribeToRunEvents(
          runId,
          0,
          (event) => {
            get().applyLiveEvent(event);
          },
          (err) => {
            console.error('SSE connection error:', err);
          },
          async () => {
            // Final authoritative GET after terminal event
            try {
              const finalState = await fetchRun(runId);
              set({ currentRun: finalState });
            } catch (e) {
              console.error('Failed to fetch final run state', e);
            }
          }
        );
        set({ activeUnsubscribe: unsubscribe });
      }
    } catch (err: any) {
      console.error('Failed to load run', err);
      set({ isLoading: false });
    }
  },

  applyLiveEvent: (event: RunEvent) => {
    const cur = get().currentRun;
    if (!cur) return;
    const next = applyEvent(cur, event);
    set({ currentRun: next });
  },

  reset: () => {
    get().activeUnsubscribe?.();
    set({ currentRun: null, isLoading: false, activeUnsubscribe: null });
  },
}));
