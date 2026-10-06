import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PlayerDock } from '../player/PlayerDock';
import { usePlayerStore } from '../../state/playerStore';

vi.mock('wavesurfer.js', () => {
  return {
    default: {
      create: vi.fn(() => ({
        on: vi.fn(),
        un: vi.fn(),
        destroy: vi.fn(),
        playPause: vi.fn(),
        play: vi.fn(),
        pause: vi.fn(),
        setTime: vi.fn(),
        setPlaybackRate: vi.fn(),
        getCurrentTime: vi.fn(() => 10),
        getDuration: vi.fn(() => 120),
      })),
    },
  };
});

vi.mock('wavesurfer.js/dist/plugins/regions.esm.js', () => {
  return {
    default: {
      create: vi.fn(() => ({
        addRegion: vi.fn(),
        clearRegions: vi.fn(),
      })),
    },
  };
});

describe('PlayerDock Component', () => {
  beforeEach(() => {
    usePlayerStore.setState({
      time: 15,
      duration: 120,
      playing: false,
      rate: 1.0,
      activeRegion: null,
      followPlayback: true,
    });
  });

  it('renders playback controls, time display, and speed options', () => {
    render(
      <PlayerDock
        audioUrl="/api/runs/123/audio"
        peaks={[0.1, 0.5, 0.8]}
        duration={120}
        segments={[{ id: 1, start: 0, end: 10, text: 'Hello' }]}
      />
    );

    // Play button
    expect(screen.getByLabelText('Play')).toBeDefined();

    // Time display (00:15 / 02:00)
    expect(screen.getByText('00:15')).toBeDefined();
    expect(screen.getByText('02:00')).toBeDefined();

    // Speed options
    expect(screen.getByText('1×')).toBeDefined();
    expect(screen.getByText('1.25×')).toBeDefined();
    expect(screen.getByText('1.5×')).toBeDefined();

    // Follow playback toggle
    expect(screen.getByText('Following')).toBeDefined();
  });

  it('displays evidence range badge when activeRegion is present and allows dismissing', () => {
    usePlayerStore.setState({
      activeRegion: { start: 10, end: 20 },
    });

    render(
      <PlayerDock
        audioUrl="/api/runs/123/audio"
        duration={120}
      />
    );

    expect(screen.getByText('yellow range = evidence')).toBeDefined();

    const clearBtn = screen.getByLabelText('Clear evidence region');
    fireEvent.click(clearBtn);

    expect(usePlayerStore.getState().activeRegion).toBeNull();
  });
});
