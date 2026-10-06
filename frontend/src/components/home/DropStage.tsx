import React, { useRef, useState } from 'react';
import { UploadCloud, FileAudio, X, AlertCircle } from 'lucide-react';
import { formatBytes, formatTime } from '../../lib/segments';
import type { AppError } from '../../api/types';

const ALLOWED_EXTENSIONS = new Set([
  'wav', 'mp3', 'm4a', 'aac', 'flac', 'ogg', 'opus', 'webm', 'mp4', 'mov', 'mkv'
]);

const MAX_UPLOAD_BYTES = 500 * 1024 * 1024; // 500 MB

const WAVEFORM_BAR_SCALES = [
  0.25, 0.4, 0.7, 0.5, 0.85, 0.75, 0.35, 0.65,
  1.0, 0.8, 0.45, 0.9, 0.95, 0.55, 0.3, 0.6,
  0.85, 1.0, 0.75, 0.4, 0.65, 0.85, 0.5, 0.35,
  0.7, 0.9, 0.65, 0.45, 0.8, 0.55, 0.3, 0.2
];

interface DropStageProps {
  selectedFile: File | null;
  duration?: number | null;
  onFileSelect: (file: File | null, duration?: number | null) => void;
  validationError: AppError | null;
  setValidationError: (err: AppError | null) => void;
}

export const DropStage: React.FC<DropStageProps> = ({
  selectedFile,
  duration,
  onFileSelect,
  validationError,
  setValidationError,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const validateAndSetFile = (file: File) => {
    // 1. Extension check
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!ALLOWED_EXTENSIONS.has(ext)) {
      setValidationError({
        code: 'UNSUPPORTED_TYPE',
        title: "That file type isn't supported",
        detail: `The file format .${ext} is not supported.`,
        fix: 'Use wav, mp3, m4a, aac, flac, ogg, opus, webm, mp4, mov or mkv',
        retryable: false,
      });
      onFileSelect(null, null);
      return;
    }

    // 2. Empty check
    if (file.size === 0) {
      setValidationError({
        code: 'EMPTY_FILE',
        title: 'That file is empty',
        detail: 'The uploaded file has a size of 0 bytes.',
        fix: 'Choose a different file',
        retryable: false,
      });
      onFileSelect(null, null);
      return;
    }

    // 3. Max size check
    if (file.size > MAX_UPLOAD_BYTES) {
      setValidationError({
        code: 'TOO_LARGE',
        title: 'The file is larger than 500 MB',
        detail: `File size (${formatBytes(file.size)}) exceeds the 500 MB limit.`,
        fix: 'Trim or compress the recording',
        retryable: false,
      });
      onFileSelect(null, null);
      return;
    }

    // Valid file!
    setValidationError(null);

    // Try reading duration from audio element
    try {
      const url = URL.createObjectURL(file);
      const audio = new Audio();
      audio.preload = 'metadata';
      audio.onloadedmetadata = () => {
        onFileSelect(file, audio.duration);
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        onFileSelect(file, null);
        URL.revokeObjectURL(url);
      };
      audio.src = url;
    } catch {
      onFileSelect(file, null);
    }
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      setIsDragging(false);
      dragCounterRef.current = 0;
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    dragCounterRef.current = 0;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleStageClick = () => {
    if (!selectedFile) {
      fileInputRef.current?.click();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!selectedFile && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onFileSelect(null, null);
    setValidationError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div style={{ marginBottom: 'var(--s5)' }}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,.mp3,.m4a,.aac,.flac,.ogg,.opus,.webm,.mp4,.mov,.mkv"
        style={{ display: 'none' }}
        onChange={handleFileInputChange}
        tabIndex={-1}
        aria-hidden="true"
      />

      <div
        className="sheet"
        role="button"
        tabIndex={0}
        onClick={handleStageClick}
        onKeyDown={handleKeyDown}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        aria-label="Upload meeting recording"
        style={{
          padding: 'var(--s6) var(--s5)',
          textAlign: 'center',
          cursor: selectedFile ? 'default' : 'pointer',
          borderColor: isDragging ? 'var(--blue)' : validationError ? 'var(--alert)' : 'var(--rule)',
          background: isDragging ? 'var(--blue-wash)' : 'var(--sheet)',
          transition: 'border-color 0.2s ease, background 0.2s ease',
          outline: 'none',
          position: 'relative',
        }}
      >
        {/* Animated Waveform Tape */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
            height: '40px',
            marginBottom: 'var(--s4)',
          }}
          aria-hidden="true"
        >
          {WAVEFORM_BAR_SCALES.map((scale, i) => {
            const activeScale = isDragging ? scale : 0.15;
            return (
              <div
                key={i}
                style={{
                  width: '3px',
                  height: '36px',
                  borderRadius: '2px',
                  backgroundColor: isDragging ? 'var(--blue)' : 'var(--ink-soft)',
                  opacity: isDragging ? 0.9 : 0.35,
                  transform: `scaleY(${activeScale})`,
                  transformOrigin: 'center',
                  transition: `transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) ${i * 8}ms, background-color 0.2s ease, opacity 0.2s ease`,
                }}
              />
            );
          })}
        </div>

        {!selectedFile ? (
          <div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '44px',
                height: '44px',
                borderRadius: '50%',
                background: isDragging ? 'var(--blue)' : 'var(--paper)',
                color: isDragging ? '#FFFFFF' : 'var(--ink-soft)',
                marginBottom: 'var(--s3)',
                transition: 'all 0.2s ease',
              }}
            >
              <UploadCloud size={24} />
            </div>

            <div style={{ fontSize: 'var(--t-lg)', fontWeight: 600, color: 'var(--ink)', marginBottom: 'var(--s1)' }}>
              Drop a meeting recording
            </div>
            <div style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-sm)' }}>
              or choose a file · wav mp3 m4a flac ogg mp4 · up to 500 MB
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: 'var(--s3) var(--s4)',
              background: 'var(--paper)',
              borderRadius: 'var(--r-ctl)',
              border: '1px solid var(--rule)',
              maxWidth: '560px',
              margin: '0 auto',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s3)', overflow: 'hidden' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '36px',
                  height: '36px',
                  borderRadius: 'var(--r-ctl)',
                  background: 'var(--blue-wash)',
                  color: 'var(--blue)',
                  flexShrink: 0,
                }}
              >
                <FileAudio size={20} />
              </div>
              <div style={{ textAlign: 'left', overflow: 'hidden' }}>
                <div
                  style={{
                    fontWeight: 600,
                    fontSize: 'var(--t-sm)',
                    color: 'var(--ink)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={selectedFile.name}
                >
                  {selectedFile.name}
                </div>
                <div style={{ fontSize: 'var(--t-xs)', color: 'var(--ink-soft)', display: 'flex', gap: 'var(--s2)' }}>
                  <span>{formatBytes(selectedFile.size)}</span>
                  {duration != null && duration > 0 && (
                    <>
                      <span>·</span>
                      <span className="tabular-nums">{formatTime(duration)}</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            <button
              type="button"
              onClick={handleRemove}
              aria-label="Remove selected file"
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                borderRadius: 'var(--r-ctl)',
                border: '1px solid var(--rule)',
                background: 'var(--sheet)',
                color: 'var(--ink-soft)',
                cursor: 'pointer',
                flexShrink: 0,
              }}
            >
              <X size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Immediate Client-Side Catalogue Error */}
      {validationError && (
        <div
          role="alert"
          style={{
            marginTop: 'var(--s2)',
            padding: 'var(--s3) var(--s4)',
            background: 'var(--alert-wash)',
            border: '1px solid var(--alert)',
            borderRadius: 'var(--r-ctl)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 'var(--s3)',
          }}
        >
          <AlertCircle size={18} color="var(--alert)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1, fontSize: 'var(--t-sm)' }}>
            <div style={{ fontWeight: 600, color: 'var(--alert)' }}>
              {validationError.title}
            </div>
            {validationError.fix && (
              <div style={{ color: 'var(--ink)', marginTop: '2px', fontSize: 'var(--t-xs)' }}>
                {validationError.fix}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
