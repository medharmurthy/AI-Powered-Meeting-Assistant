import React, { useEffect, useState } from 'react';

interface NavItem {
  id: string;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'section-summary', label: 'Summary' },
  { id: 'section-minutes', label: 'Minutes' },
  { id: 'section-decisions', label: 'Decisions' },
  { id: 'section-unresolved', label: 'Not settled' },
  { id: 'section-tasks', label: 'Tasks' },
];

export const RecordNav: React.FC = () => {
  const [activeId, setActiveId] = useState<string>('section-summary');

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
            break;
          }
        }
      },
      {
        rootMargin: '-20% 0px -70% 0px',
        threshold: 0,
      }
    );

    NAV_ITEMS.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActiveId(id);
    }
  };

  return (
    <nav
      aria-label="Record sections"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 5,
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--s2)',
        padding: '8px var(--s5)',
        background: 'var(--sheet)',
        borderBottom: '1px solid var(--rule)',
        overflowX: 'auto',
      }}
    >
      {NAV_ITEMS.map((item) => {
        const isActive = activeId === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => scrollTo(item.id)}
            style={{
              background: 'none',
              border: 'none',
              padding: '4px 8px',
              borderRadius: 'var(--r-ctl)',
              fontSize: 'var(--t-xs)',
              fontWeight: isActive ? 700 : 500,
              color: isActive ? 'var(--blue)' : 'var(--ink-soft)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'color 0.15s ease',
            }}
          >
            {item.label}
          </button>
        );
      })}
    </nav>
  );
};
