import { create } from 'zustand';

interface FocusStoreState {
  hoverIds: number[];
  pinnedIds: number[];
  setHover: (ids: number[]) => void;
  clearHover: () => void;
  togglePin: (ids: number[]) => void;
  clearPin: () => void;
  clearAll: () => void;
}

export const useFocusStore = create<FocusStoreState>((set) => ({
  hoverIds: [],
  pinnedIds: [],

  setHover: (ids: number[]) => set({ hoverIds: ids }),
  clearHover: () => set({ hoverIds: [] }),

  togglePin: (ids: number[]) =>
    set((state) => {
      // If already pinned to these exact ids, toggle off
      const isSame =
        state.pinnedIds.length === ids.length &&
        state.pinnedIds.every((id, idx) => id === ids[idx]);
      return { pinnedIds: isSame ? [] : ids };
    }),

  clearPin: () => set({ pinnedIds: [] }),
  clearAll: () => set({ hoverIds: [], pinnedIds: [] }),
}));
