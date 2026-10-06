import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SegmentRow } from '../transcript/SegmentRow';
import { CorrectionPopover } from '../transcript/CorrectionPopover';
import { ChangesSummary } from '../transcript/ChangesSummary';
import { CompareRow, CollapsedUnchanged } from '../transcript/CompareRow';
import { usePlayerStore } from '../../state/playerStore';
import { useRunStore, initialRunState } from '../../state/runStore';
import * as client from '../../api/client';
import type { Correction, Segment } from '../../api/types';

vi.mock('../../api/client', () => ({
  patchCorrection: vi.fn(() => Promise.resolve({ status: 'ok', record_stale: true })),
}));

describe('Transcript Components', () => {
  beforeEach(() => {
    usePlayerStore.setState({
      time: 0,
      duration: 100,
      playing: false,
    });
  });

  describe('SegmentRow', () => {
    const dummySeg: Segment = {
      id: 5,
      start: 25.0,
      end: 30.0,
      text: 'We deploy the new cache layer.',
    };

    it('renders time gutter and segment text', () => {
      render(<SegmentRow segment={dummySeg} />);
      expect(screen.getByText('00:25')).toBeDefined();
      expect(screen.getByText('We deploy the new cache layer.')).toBeDefined();
    });

    it('highlights active line when current player time is inside segment range', () => {
      usePlayerStore.setState({ time: 27.5 });
      const { container } = render(<SegmentRow segment={dummySeg} />);

      const row = container.querySelector('#seg-5') as HTMLElement;
      expect(row).toBeDefined();
      expect(row.style.borderLeft).toContain('var(--blue)');
    });

    it('seeks to segment start time when clicking the time gutter', () => {
      const mockSeek = vi.fn();
      usePlayerStore.getState().registerController({
        seek: mockSeek,
        playRange: vi.fn(),
        toggle: vi.fn(),
        setRate: vi.fn(),
      });

      render(<SegmentRow segment={dummySeg} />);
      const gutterBtn = screen.getByTitle('Click to seek and play from 00:25');
      fireEvent.click(gutterBtn);

      expect(mockSeek).toHaveBeenCalledWith(25.0);
    });
  });

  describe('CorrectionPopover', () => {
    const dummyCorrection: Correction = {
      id: 'c1',
      segment_id: 2,
      original: 'Memcatch',
      corrected: 'Memcached',
      reason: 'Misheard caching tool',
      status: 'applied',
    };

    it('renders struck-through original, corrected, reason, and toggles status', async () => {
      useRunStore.setState({
        currentRun: {
          ...initialRunState,
          id: 'run-99',
          corrections: [dummyCorrection],
          recordStale: false,
        },
      });

      render(
        <CorrectionPopover
          runId="run-99"
          correction={dummyCorrection}
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText('Memcatch')).toBeDefined();
      expect(screen.getByText('Memcached')).toBeDefined();
      expect(screen.getByText('Misheard caching tool')).toBeDefined();

      const switchBtn = screen.getByRole('switch');
      expect(switchBtn.getAttribute('aria-checked')).toBe('true');

      fireEvent.click(switchBtn);

      await waitFor(() => {
        expect(client.patchCorrection).toHaveBeenCalledWith('run-99', 'c1', false);
      });

      expect(useRunStore.getState().currentRun?.recordStale).toBe(true);
    });
  });

  describe('ChangesSummary', () => {
    const corrections: Correction[] = [
      {
        id: 'c1',
        segment_id: 1,
        original: 'cooper netties',
        corrected: 'Kubernetes',
        reason: 'Proper noun',
        status: 'applied',
      },
      {
        id: 'c2',
        segment_id: 3,
        original: 'five',
        corrected: '50',
        reason: 'Spelling',
        status: 'blocked',
        block_reason: 'Numbers, amounts, and dates must never change',
      },
    ];

    it('renders applied count and expandable blocked guardrails list', () => {
      render(<ChangesSummary corrections={corrections} />);

      expect(screen.getByText(/1 correction applied, 1 blocked by safety checks/)).toBeDefined();

      const expandBtn = screen.getByText('Review blocked edits');
      fireEvent.click(expandBtn);

      expect(screen.getByText('five')).toBeDefined();
      expect(screen.getByText('50')).toBeDefined();
      expect(screen.getByText(/Numbers, amounts, and dates must never change/)).toBeDefined();
    });
  });

  describe('CompareRow and CollapsedUnchanged', () => {
    it('renders CompareRow with 50/50 raw and refined columns', () => {
      render(
        <CompareRow
          segmentId={1}
          rawText="Raw words here"
          refinedText="Refined words here"
          start={12}
          isModified={true}
        />
      );

      expect(screen.getByText('00:12')).toBeDefined();
      expect(screen.getByText('Raw words here')).toBeDefined();
      expect(screen.getByText('Refined words here')).toBeDefined();
    });

    it('collapses unchanged rows and expands on click', () => {
      const items = [
        {
          raw: { id: 1, start: 0, end: 2, text: 'Unchanged 1' },
          refined: { id: 1, start: 0, end: 2, text: 'Unchanged 1', spans: [] },
        },
        {
          raw: { id: 2, start: 3, end: 5, text: 'Unchanged 2' },
          refined: { id: 2, start: 3, end: 5, text: 'Unchanged 2', spans: [] },
        },
      ];

      render(<CollapsedUnchanged count={2} segments={items} />);
      expect(screen.getByText(/2 lines unchanged \(click to expand\)/)).toBeDefined();

      fireEvent.click(screen.getByText(/2 lines unchanged/));
      expect(screen.getAllByText('Unchanged 1').length).toBe(2);
      expect(screen.getAllByText('Unchanged 2').length).toBe(2);
    });
  });
});
