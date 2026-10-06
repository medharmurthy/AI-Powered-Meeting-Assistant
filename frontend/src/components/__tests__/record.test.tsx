import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Unspecified } from '../record/Unspecified';
import { EvidenceChip } from '../record/EvidenceChip';
import { DecisionsSection } from '../record/DecisionsSection';
import { TasksSection } from '../record/TasksSection';
import { RecordPane } from '../record/RecordPane';
import { useFocusStore } from '../../state/focusStore';
import type { Decision, ActionItem, RunState, Segment } from '../../api/types';

describe('Record Components', () => {
  describe('Unspecified Pill', () => {
    it('renders literal Unspecified text with aria-label', () => {
      render(<Unspecified />);
      const pill = screen.getByLabelText('Unspecified');
      expect(pill).toBeDefined();
      expect(pill.textContent).toBe('Unspecified');
    });
  });

  describe('EvidenceChip', () => {
    const dummySegments: Segment[] = [
      { id: 1, start: 65, end: 70, text: 'First segment' },
      { id: 2, start: 71, end: 75, text: 'Second segment' },
    ];

    it('renders formatted start time and extra segments count', () => {
      render(<EvidenceChip segmentIds={[1, 2]} segments={dummySegments} />);
      expect(screen.getByText('01:05')).toBeDefined();
      expect(screen.getByText('+1')).toBeDefined();
    });

    it('toggles pin in focusStore and scrolls on click', () => {
      render(<EvidenceChip segmentIds={[1]} segments={dummySegments} />);
      const btn = screen.getByTitle('Cites segment 1');
      fireEvent.click(btn);

      const storeState = useFocusStore.getState();
      expect(storeState.pinnedIds).toContain(1);
    });
  });

  describe('DecisionsSection', () => {
    it('renders empty state when no decisions were agreed', () => {
      render(<DecisionsSection decisions={[]} isWriting={false} />);
      expect(screen.getByText('No decisions were agreed in this recording.')).toBeDefined();
    });

    it('renders decisions with id, rationale, and quote', () => {
      const decisions: Decision[] = [
        {
          id: 'D1',
          text: 'Migrate the session cache to Redis',
          rationale: 'Redis latency is 5x lower',
          quote: 'Then it is decided: Redis.',
          segment_ids: [1],
        },
      ];

      render(<DecisionsSection decisions={decisions} />);
      expect(screen.getByText('Migrate the session cache to Redis')).toBeDefined();
      expect(screen.getByText('Redis latency is 5x lower')).toBeDefined();
      expect(screen.getByText('“Then it is decided: Redis.”')).toBeDefined();
    });
  });

  describe('TasksSection', () => {
    it('renders empty state when no tasks were assigned', () => {
      render(<TasksSection actions={[]} isWriting={false} />);
      expect(screen.getByText('No tasks were assigned in this recording.')).toBeDefined();
    });

    it('renders Unspecified for missing owner or deadline', () => {
      const actions: ActionItem[] = [
        {
          id: 'T1',
          task: 'Benchmark query performance',
          owner: null,
          deadline: null,
          segment_ids: [1],
        },
        {
          id: 'T2',
          task: 'Deploy canary build',
          owner: 'Dan',
          deadline: 'Friday',
          segment_ids: [2],
        },
      ];

      render(<TasksSection actions={actions} />);
      expect(screen.getByText('Benchmark query performance')).toBeDefined();
      expect(screen.getByText('Deploy canary build')).toBeDefined();
      expect(screen.getByText('Dan')).toBeDefined();
      expect(screen.getByText('Friday')).toBeDefined();

      const unspecifiedPills = screen.getAllByLabelText('Unspecified');
      expect(unspecifiedPills.length).toBe(2);
    });
  });

  describe('RecordPane', () => {
    it('renders header, sticky nav, and sections with full run state', () => {
      const mockRun: RunState = {
        id: 'run-123',
        filename: 'planning_sync.mp3',
        status: 'done',
        stage: null,
        models: {},
        timings: {},
        progress: {},
        raw: [],
        refined: null,
        corrections: [],
        record: {
          title: 'Planning Sync',
          summary: 'We reviewed the Q3 roadmap and established milestones.',
          attendees: ['Maya', 'Dan'],
          minutes: [
            {
              title: 'Infrastructure updates',
              points: [{ text: 'Database load decreased by 20%.', segment_ids: [] }],
            },
          ],
          decisions: [],
          unresolved: [],
          action_items: [],
          dropped: [
            {
              section: 'decisions',
              text: 'Unverified claim',
              reason: 'No speaker agreement',
            },
          ],
        },
        recordStale: false,
        warnings: [],
      };

      render(<RecordPane run={mockRun} />);
      expect(screen.getByText('Planning Sync')).toBeDefined();
      expect(screen.getByText('Maya')).toBeDefined();
      expect(screen.getByText('Dan')).toBeDefined();
      expect(screen.getByText('We reviewed the Q3 roadmap and established milestones.')).toBeDefined();
      expect(screen.getByText('Infrastructure updates')).toBeDefined();
      expect(screen.getByText('1 model suggestion removed')).toBeDefined();
    });
  });
});
