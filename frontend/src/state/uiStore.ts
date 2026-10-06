import { create } from 'zustand';

export type Theme = 'light' | 'dark';
export type ViewTab = 'raw' | 'refined' | 'compare';

interface UIStoreState {
  theme: Theme;
  splitRatio: number; // percentage for left pane (default 46)
  viewTab: ViewTab;
  toggleTheme: () => void;
  setSplitRatio: (ratio: number) => void;
  setViewTab: (tab: ViewTab) => void;
}

function getInitialTheme(): Theme {
  const saved = localStorage.getItem('verbatim-theme');
  if (saved === 'light' || saved === 'dark') {
    return saved;
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyThemeToDocument(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('verbatim-theme', theme);
}

const initialTheme = getInitialTheme();
applyThemeToDocument(initialTheme);

export const useUIStore = create<UIStoreState>((set, get) => ({
  theme: initialTheme,
  splitRatio: parseFloat(localStorage.getItem('verbatim-split-ratio') || '46'),
  viewTab: 'raw',

  toggleTheme: () => {
    const nextTheme: Theme = get().theme === 'light' ? 'dark' : 'light';
    applyThemeToDocument(nextTheme);
    set({ theme: nextTheme });
  },

  setSplitRatio: (ratio: number) => {
    const clamped = Math.max(25, Math.min(75, ratio));
    localStorage.setItem('verbatim-split-ratio', clamped.toString());
    set({ splitRatio: clamped });
  },

  setViewTab: (tab: ViewTab) => {
    set({ viewTab: tab });
  },
}));
