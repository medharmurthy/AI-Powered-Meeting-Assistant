import { describe, it, expect } from 'vitest';
import { applyEvent, initialRunState } from '../runStore';
import type { RunEvent, RunState } from '../../api/types';

describe('RunStore Reducer (applyEvent)', () => {
  it('processes a full pipeline event sequence sequentially into comprehensive RunState', () => {
    let state: RunState = { ...initialRunState, id: 'test-run-1', filename: 'meeting.mp3' };

    const eventSequence: RunEvent[] = [
      {
        seq: 1,
        type: 'run.queued',
        data: { position: 1 },
        t: 100,
      },
      {
        seq: 2,
        type: 'run.started',
        data: {
          from_stage: 'ingest',
          models: { stt: 'distil-large-v3', refiner: 'qwen3:8b', documenter: 'gemma3:12b' },
          profile: 'standard',
        },
        t: 101,
      },
      {
        seq: 3,
        type: 'stage.started',
        data: { stage: 'ingest' },
        t: 102,
      },
      {
        seq: 4,
        type: 'audio.ready',
        data: {
          duration: 115.5,
          audio_url: '/api/runs/test-run-1/audio',
          peaks_url: '/api/runs/test-run-1/peaks',
        },
        t: 103,
      },
      {
        seq: 5,
        type: 'stage.done',
        data: { stage: 'ingest', seconds: 0.45 },
        t: 104,
      },
      {
        seq: 6,
        type: 'stage.started',
        data: { stage: 'transcribe', model: 'distil-large-v3' },
        t: 105,
      },
      {
        seq: 7,
        type: 'transcript.segment',
        data: { id: 0, start: 0.0, end: 3.2, text: "Okay, let's get started.", words: [] },
        t: 106,
      },
      {
        seq: 8,
        type: 'stage.progress',
        data: { stage: 'transcribe', done: 3.2, total: 115.5, label: 'Listening 00:03 of 01:55' },
        t: 107,
      },
      {
        seq: 9,
        type: 'transcript.segment',
        data: { id: 1, start: 3.5, end: 8.0, text: 'We migrate to Redis.', words: [] },
        t: 108,
      },
      {
        seq: 10,
        type: 'stage.done',
        data: { stage: 'transcribe', seconds: 4.1 },
        t: 109,
      },
      {
        seq: 11,
        type: 'stage.started',
        data: { stage: 'refine', model: 'qwen3:8b' },
        t: 110,
      },
      {
        seq: 12,
        type: 'refine.profile',
        data: {
          topic: 'Architecture sync',
          domain: 'backend',
          likely_terms: ['Redis', 'PostgreSQL'],
          names: ['Maya', 'Dan'],
        },
        t: 111,
      },
      {
        seq: 13,
        type: 'refine.correction',
        data: {
          id: 'c1',
          segment_id: 1,
          original: 'redis',
          corrected: 'Redis',
          reason: 'Capitalize product name',
          status: 'applied',
        },
        t: 112,
      },
      {
        seq: 14,
        type: 'refine.blocked',
        data: {
          id: 'c2',
          segment_id: 1,
          original: '1',
          corrected: '2',
          reason: 'Changed digit',
          status: 'blocked',
          block_reason: 'Would change a number',
        },
        t: 113,
      },
      {
        seq: 15,
        type: 'refine.done',
        data: {
          segments: [
            { id: 0, start: 0.0, end: 3.2, text: "Okay, let's get started.", spans: [] },
            { id: 1, start: 3.5, end: 8.0, text: 'We migrate to Redis.', spans: [{ start: 14, end: 19, correction_id: 'c1' }] },
          ],
          corrections: [
            { id: 'c1', segment_id: 1, original: 'redis', corrected: 'Redis', reason: 'Capitalize', status: 'applied' },
            { id: 'c2', segment_id: 1, original: '1', corrected: '2', reason: 'Digit', status: 'blocked', block_reason: 'Would change a number' },
          ],
        },
        t: 114,
      },
      {
        seq: 16,
        type: 'stage.done',
        data: { stage: 'refine', seconds: 2.3 },
        t: 115,
      },
      {
        seq: 17,
        type: 'stage.started',
        data: { stage: 'document', model: 'gemma3:12b' },
        t: 116,
      },
      {
        seq: 18,
        type: 'record.section',
        data: {
          section: 'summary',
          data: {
            title: 'Orion payments sync',
            summary: 'The team approved the Redis migration.',
            attendees: ['Maya', 'Dan'],
          },
        },
        t: 117,
      },
      {
        seq: 19,
        type: 'record.section',
        data: {
          section: 'decisions',
          data: {
            decisions: [{ id: 'D1', text: 'Migrate to Redis', segment_ids: [1] }],
            unresolved: [{ id: 'U1', kind: 'deferred', text: 'gRPC migration', segment_ids: [] }],
          },
        },
        t: 118,
      },
      {
        seq: 20,
        type: 'record.section',
        data: {
          section: 'actions',
          data: {
            action_items: [{ id: 'T1', task: 'Write module', owner: 'Dan', deadline: 'by Thursday', segment_ids: [1] }],
          },
        },
        t: 119,
      },
      {
        seq: 21,
        type: 'stage.done',
        data: { stage: 'document', seconds: 5.4 },
        t: 120,
      },
      {
        seq: 22,
        type: 'run.done',
        data: {},
        t: 121,
      },
    ];

    // Apply all events sequentially
    for (const event of eventSequence) {
      state = applyEvent(state, event);
    }

    // Verify final state properties
    expect(state.status).toBe('done');
    expect(state.stage).toBeNull();
    expect(state.duration).toBe(115.5);
    expect(state.audioUrl).toBe('/api/runs/test-run-1/audio');
    expect(state.models.stt).toBe('distil-large-v3');
    expect(state.models.refiner).toBe('qwen3:8b');
    expect(state.models.documenter).toBe('gemma3:12b');
    expect(state.timings.ingest).toBe(0.45);
    expect(state.timings.transcribe).toBe(4.1);
    expect(state.timings.refine).toBe(2.3);
    expect(state.timings.document).toBe(5.4);
    expect(state.raw).toHaveLength(2);
    expect(state.raw[0].text).toBe("Okay, let's get started.");
    expect(state.raw[1].text).toBe('We migrate to Redis.');
    expect(state.profile?.domain).toBe('backend');
    expect(state.corrections).toHaveLength(2);
    expect(state.corrections[1].status).toBe('blocked');
    expect(state.corrections[1].block_reason).toBe('Would change a number');
    expect(state.refined).toHaveLength(2);
    expect(state.record.title).toBe('Orion payments sync');
    expect(state.record.decisions).toHaveLength(1);
    expect(state.record.unresolved).toHaveLength(1);
    expect(state.record.action_items).toHaveLength(1);
  });

  it('handles run.failed and warning events gracefully', () => {
    let state: RunState = { ...initialRunState, id: 'err-run' };

    state = applyEvent(state, {
      seq: 1,
      type: 'warning',
      data: { code: 'GPU_FALLBACK', title: 'Running on CPU', detail: 'No CUDA', retryable: false },
      t: 10,
    });
    expect(state.warnings).toHaveLength(1);
    expect(state.warnings[0].code).toBe('GPU_FALLBACK');

    state = applyEvent(state, {
      seq: 2,
      type: 'run.failed',
      data: { code: 'SILENT_AUDIO', title: 'Recording is silent', detail: 'RMS too low', retryable: false },
      t: 11,
    });
    expect(state.status).toBe('failed');
    expect(state.error?.code).toBe('SILENT_AUDIO');
  });
});
