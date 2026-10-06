import type { RunEvent } from './types';

export function subscribeToRunEvents(
  runId: string,
  afterSeq: number = 0,
  onEvent: (event: RunEvent) => void,
  onError?: (err: any) => void,
  onTerminal?: () => void
): () => void {
  const url = `/api/runs/${runId}/events?after=${afterSeq}`;
  const es = new EventSource(url);

  const eventTypes = [
    'run.queued',
    'run.started',
    'stage.started',
    'stage.progress',
    'stage.done',
    'audio.ready',
    'transcript.segment',
    'refine.profile',
    'refine.correction',
    'refine.blocked',
    'refine.done',
    'record.section',
    'warning',
    'run.done',
    'run.failed',
  ];

  eventTypes.forEach((type) => {
    es.addEventListener(type, (e: MessageEvent) => {
      try {
        const seq = parseInt(e.lastEventId || '0', 10);
        const data = e.data ? JSON.parse(e.data) : {};
        const runEvent: RunEvent = {
          seq,
          type,
          data,
          t: Date.now() / 1000,
        };
        onEvent(runEvent);

        if (type === 'run.done' || type === 'run.failed') {
          es.close();
          onTerminal?.();
        }
      } catch (err) {
        console.error('Failed to parse SSE event data', err);
      }
    });
  });

  es.onerror = (err) => {
    onError?.(err);
  };

  return () => {
    es.close();
  };
}
