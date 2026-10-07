import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportSection } from '../record/ExportSection';
import type { RunState } from '../../api/types';

describe('ExportSection Component', () => {
  const mockRun: RunState = {
    id: 'run-test-export-123',
    filename: 'test_meeting.mp3',
    status: 'done',
    stage: null,
    models: { stt: 'whisper', refiner: 'qwen', documenter: 'gemma' },
    timings: {},
    progress: {},
    raw: [],
    refined: null,
    corrections: [],
    record: {
      title: 'Cache Migration Review',
      summary: 'Team decided to migrate to Redis.',
      attendees: ['Maya', 'Dan', 'Priya'],
      minutes: [],
      decisions: [
        { id: 'D1', text: 'Migrate to Redis', segment_ids: [1] },
        { id: 'D2', text: 'Do not upgrade PostgreSQL', segment_ids: [2] },
      ],
      unresolved: [],
      action_items: [
        { id: 'T1', task: 'Write Terraform module', owner: 'Dan', deadline: 'by Thursday', segment_ids: [3] },
      ],
      dropped: [],
    },
    recordStale: false,
    warnings: [],
    exportParity: {
      decisions: 2,
      tasks: 1,
      ok: true,
    },
  };

  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      text: async () => '# Sample Export Preview',
    }));
  });

  it('renders section title and primary ZIP download button', async () => {
    render(<ExportSection run={mockRun} />);
    expect(screen.getByText('Export Deliverables')).toBeDefined();

    const zipBtn = screen.getByText('Download everything (.zip)');
    expect(zipBtn).toBeDefined();
    expect(zipBtn.closest('a')?.getAttribute('href')).toContain('/api/runs/run-test-export-123/export/bundle.zip');
    await waitFor(() => expect(screen.getByText('Live preview of generated export')).toBeDefined());
  });

  it('renders matching parity line correctly', async () => {
    render(<ExportSection run={mockRun} />);
    const parityLine = screen.getByText('Markdown and JSON contain the same 2 decisions and 1 task');
    expect(parityLine).toBeDefined();
    await waitFor(() => expect(screen.getByText('Live preview of generated export')).toBeDefined());
  });

  it('renders alert when parity fails', async () => {
    const runMismatch: RunState = {
      ...mockRun,
      exportParity: {
        decisions: 2,
        tasks: 1,
        ok: false,
      },
    };
    render(<ExportSection run={runMismatch} />);
    expect(screen.getByText(/Parity discrepancy detected/)).toBeDefined();
    await waitFor(() => expect(screen.getByText('Live preview of generated export')).toBeDefined());
  });

  it('renders all 9 export deliverables with download links', async () => {
    render(<ExportSection run={mockRun} />);
    expect(screen.getByText('meeting_record.md')).toBeDefined();
    expect(screen.getByText('meeting_record.json')).toBeDefined();
    expect(screen.getByText('raw_transcript.txt')).toBeDefined();
    expect(screen.getByText('raw_transcript.srt')).toBeDefined();
    expect(screen.getByText('raw_transcript.json')).toBeDefined();
    expect(screen.getByText('refined_transcript.txt')).toBeDefined();
    expect(screen.getByText('refined_transcript.json')).toBeDefined();
    expect(screen.getByText('corrections.csv')).toBeDefined();
    expect(screen.getByText('bundle.zip')).toBeDefined();
    await waitFor(() => expect(screen.getByText('Live preview of generated export')).toBeDefined());
  });

  it('toggles between Readable and Structured preview tabs', async () => {
    render(<ExportSection run={mockRun} />);
    const readableTab = screen.getByText('Readable (Markdown)');
    const structuredTab = screen.getByText('Structured (JSON)');

    expect(readableTab).toBeDefined();
    expect(structuredTab).toBeDefined();

    fireEvent.click(structuredTab);
    await waitFor(() => expect(screen.getByText('Live preview of generated export')).toBeDefined());
  });
});
