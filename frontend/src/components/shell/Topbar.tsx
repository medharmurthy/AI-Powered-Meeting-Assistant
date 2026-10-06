import React from 'react';
import { ChevronRight } from 'lucide-react';
import { HealthPill } from './HealthPill';
import { ThemeToggle } from './ThemeToggle';

interface TopbarProps {
  runTitle?: string;
}

export const Topbar: React.FC<TopbarProps> = ({ runTitle }) => {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <a href="/" style={{ color: 'inherit', textDecoration: 'none' }}>
          Verbatim
        </a>
        {runTitle && (
          <div className="topbar-crumb">
            <ChevronRight size={14} />
            <span>{runTitle}</span>
          </div>
        )}
      </div>

      <div className="topbar-actions">
        <HealthPill />
        <ThemeToggle />
      </div>
    </header>
  );
};
