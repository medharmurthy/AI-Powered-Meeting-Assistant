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
  try {
    if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
      const saved = localStorage.getItem('verbatim-theme');
      if (saved === 'light' || saved === 'dark') {
        return saved;
      }
    }
    if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
  } catch {
    // ignore
  }
  return 'light';
}

function applyThemeToDocument(theme: Theme) {
  try {
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme);
    }
    if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
      localStorage.setItem('verbatim-theme', theme);
    }
  } catch {
    // ignore
  }
}

function getInitialSplitRatio(): number {
  try {
    if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
      const saved = localStorage.getItem('verbatim-split-ratio');
      if (saved) {
        const parsed = parseFloat(saved);
        if (!isNaN(parsed) && parsed >= 20 && parsed <= 80) {
          return parsed;
        }
      }
    }
  } catch {
    // ignore
  }
  return 46;
}

const initialTheme = getInitialTheme();
applyThemeToDocument(initialTheme);

export const useUIStore = create<UIStoreState>((set, get) => ({
  theme: initialTheme,
  splitRatio: getInitialSplitRatio(),
  viewTab: 'raw',

  toggleTheme: () => {
    const nextTheme: Theme = get().theme === 'light' ? 'dark' : 'light';
    applyThemeToDocument(nextTheme);
    set({ theme: nextTheme });
  },

  setSplitRatio: (ratio: number) => {
    try {
      if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
        localStorage.setItem('verbatim-split-ratio', ratio.toString());
      }
    } catch {
      // ignore
    }
    set({ splitRatio: ratio });
  },

  setViewTab: (tab: ViewTab) => {
    set({ viewTab: tab });
  },
}));
