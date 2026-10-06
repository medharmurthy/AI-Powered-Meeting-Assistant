import React, { useState } from 'react';
import { X } from 'lucide-react';

interface ChipInputProps {
  label: string;
  placeholder?: string;
  chips: string[];
  onChange: (chips: string[]) => void;
  maxChips?: number;
}

export const ChipInput: React.FC<ChipInputProps> = ({
  label,
  placeholder = 'Add…',
  chips,
  onChange,
  maxChips = 40,
}) => {
  const [inputValue, setInputValue] = useState('');

  const addChips = (raw: string) => {
    const tokens = raw
      .split(/[,;\n]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0 && !chips.includes(t));

    if (tokens.length === 0) return;

    const combined = [...chips, ...tokens].slice(0, maxChips);
    onChange(combined);
    setInputValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addChips(inputValue);
    } else if (e.key === 'Backspace' && inputValue === '' && chips.length > 0) {
      e.preventDefault();
      onChange(chips.slice(0, -1));
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text');
    addChips(pasted);
  };

  const removeChip = (indexToRemove: number) => {
    onChange(chips.filter((_, idx) => idx !== indexToRemove));
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--s1)' }}>
      <label style={{ fontSize: 'var(--t-xs)', fontWeight: 600, color: 'var(--ink-soft)' }}>
        {label}
      </label>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 'var(--s2)',
          padding: '6px 10px',
          background: 'var(--sheet)',
          border: '1px solid var(--rule)',
          borderRadius: 'var(--r-ctl)',
          minHeight: '38px',
        }}
      >
        {chips.map((chip, idx) => (
          <span
            key={`${chip}-${idx}`}
            className="chip-pill"
            style={{
              background: 'var(--blue-wash)',
              color: 'var(--blue)',
              border: '1px solid var(--blue)',
              padding: '2px 8px',
            }}
          >
            <span>{chip}</span>
            <button
              type="button"
              onClick={() => removeChip(idx)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                padding: 0,
                color: 'var(--blue)',
              }}
              aria-label={`Remove ${chip}`}
            >
              <X size={12} />
            </button>
          </span>
        ))}

        {chips.length < maxChips && (
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            onBlur={() => inputValue && addChips(inputValue)}
            placeholder={chips.length === 0 ? placeholder : ''}
            style={{
              flex: 1,
              minWidth: '80px',
              border: 'none',
              outline: 'none',
              background: 'transparent',
              color: 'var(--ink)',
              fontSize: 'var(--t-sm)',
            }}
          />
        )}
      </div>
    </div>
  );
};
