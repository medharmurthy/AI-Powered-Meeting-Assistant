import { create } from 'zustand';

interface PlayerStoreState {
  time: number;
  playing: boolean;
  duration: number;
  rate: number;
  activeRegion: { start: number; end: number } | null;
  followPlayback: boolean;

  // Registered actions from the PlayerDock WaveSurfer controller
  _seekHandler: ((t: number) => void) | null;
  _playRangeHandler: ((start: number, end: number) => void) | null;
  _toggleHandler: (() => void) | null;
  _rateHandler: ((rate: number) => void) | null;

  registerController: (handlers: {
    seek: (t: number) => void;
    playRange: (start: number, end: number) => void;
    toggle: () => void;
    setRate: (rate: number) => void;
  }) => void;
  unregisterController: () => void;

  seek: (t: number) => void;
  playRange: (start: number, end: number) => void;
  toggle: () => void;
  setRate: (rate: number) => void;
  setTime: (t: number) => void;
  setPlaying: (playing: boolean) => void;
  setDuration: (duration: number) => void;
  setActiveRegion: (region: { start: number; end: number } | null) => void;
  setFollowPlayback: (follow: boolean) => void;
}

export const usePlayerStore = create<PlayerStoreState>((set, get) => ({
  time: 0,
  playing: false,
  duration: 0,
  rate: 1.0,
  activeRegion: null,
  followPlayback: true,

  _seekHandler: null,
  _playRangeHandler: null,
  _toggleHandler: null,
  _rateHandler: null,

  registerController: (handlers) => {
    set({
      _seekHandler: handlers.seek,
      _playRangeHandler: handlers.playRange,
      _toggleHandler: handlers.toggle,
      _rateHandler: handlers.setRate,
    });
  },

  unregisterController: () => {
    set({
      _seekHandler: null,
      _playRangeHandler: null,
      _toggleHandler: null,
      _rateHandler: null,
    });
  },

  seek: (t: number) => {
    const handler = get()._seekHandler;
    if (handler) {
      handler(t);
    }
    set({ time: t });
  },

  playRange: (start: number, end: number) => {
    const clampedStart = Math.max(0, start);
    const clampedEnd = Math.max(clampedStart + 0.1, end);
    set({ activeRegion: { start: clampedStart, end: clampedEnd } });

    const handler = get()._playRangeHandler;
    if (handler) {
      handler(clampedStart, clampedEnd);
    }
  },

  toggle: () => {
    const handler = get()._toggleHandler;
    if (handler) {
      handler();
    }
  },

  setRate: (rate: number) => {
    set({ rate });
    const handler = get()._rateHandler;
    if (handler) {
      handler(rate);
    }
  },

  setTime: (time: number) => set({ time }),
  setPlaying: (playing: boolean) => set({ playing }),
  setDuration: (duration: number) => set({ duration }),
  setActiveRegion: (activeRegion) => set({ activeRegion }),
  setFollowPlayback: (followPlayback) => set({ followPlayback }),
}));
