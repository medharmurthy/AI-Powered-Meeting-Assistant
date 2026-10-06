import { describe, it, expect, vi, beforeEach } from 'vitest';
import { usePlayerStore } from '../playerStore';

describe('PlayerStore', () => {
  beforeEach(() => {
    usePlayerStore.setState({
      time: 0,
      playing: false,
      duration: 120,
      rate: 1.0,
      activeRegion: null,
      followPlayback: true,
      _seekHandler: null,
      _playRangeHandler: null,
      _toggleHandler: null,
      _rateHandler: null,
    });
  });

  it('updates time, playing state, duration, and rate', () => {
    const store = usePlayerStore.getState();
    store.setTime(45.5);
    store.setPlaying(true);
    store.setDuration(180);
    store.setRate(1.25);

    const updated = usePlayerStore.getState();
    expect(updated.time).toBe(45.5);
    expect(updated.playing).toBe(true);
    expect(updated.duration).toBe(180);
    expect(updated.rate).toBe(1.25);
  });

  it('dispatches seek, toggle, and playRange to registered controllers', () => {
    const mockSeek = vi.fn();
    const mockPlayRange = vi.fn();
    const mockToggle = vi.fn();
    const mockSetRate = vi.fn();

    const store = usePlayerStore.getState();
    store.registerController({
      seek: mockSeek,
      playRange: mockPlayRange,
      toggle: mockToggle,
      setRate: mockSetRate,
    });

    store.seek(30);
    expect(mockSeek).toHaveBeenCalledWith(30);
    expect(usePlayerStore.getState().time).toBe(30);

    store.toggle();
    expect(mockToggle).toHaveBeenCalledTimes(1);

    store.playRange(10, 25);
    expect(mockPlayRange).toHaveBeenCalledWith(10, 25);
    expect(usePlayerStore.getState().activeRegion).toEqual({ start: 10, end: 25 });

    store.setRate(1.5);
    expect(mockSetRate).toHaveBeenCalledWith(1.5);
    expect(usePlayerStore.getState().rate).toBe(1.5);
  });

  it('toggles followPlayback mode', () => {
    const store = usePlayerStore.getState();
    expect(store.followPlayback).toBe(true);

    store.setFollowPlayback(false);
    expect(usePlayerStore.getState().followPlayback).toBe(false);
  });
});
