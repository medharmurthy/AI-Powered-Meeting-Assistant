import React, { useState, useEffect } from 'react';
import { Download, CheckCircle2, AlertTriangle, Archive, Code2, Eye } from 'lucide-react';
import type { RunState } from '../../api/types';
import { getExportUrl } from '../../api/client';

interface ExportSectionProps {
  run: RunState;
}

interface ExportFileDef {
  name: string;
  format: string;
  desc: string;
}

const EXPORT_FILES: ExportFileDef[] = [
  { name: 'meeting_record.md', format: 'MD', desc: 'Executive report and action items' },
  { name: 'meeting_record.json', format: 'JSON', desc: 'Full machine-readable record' },
  { name: 'raw_transcript.txt', format: 'TXT', desc: 'Raw ASR transcript with timestamps' },
  { name: 'raw_transcript.srt', format: 'SRT', desc: 'Standard subtitle track' },
  { name: 'raw_transcript.json', format: 'JSON', desc: 'ASR segments and word timestamps' },
  { name: 'refined_transcript.txt', format: 'TXT', desc: 'Cleaned transcript with timestamps' },
  { name: 'refined_transcript.json', format: 'JSON', desc: 'Refined segments with correction spans' },
  { name: 'corrections.csv', format: 'CSV', desc: 'Applied and proposed term corrections' },
  { name: 'bundle.zip', format: 'ZIP', desc: 'Complete archive of all 8 export files' },
];

export const ExportSection: React.FC<ExportSectionProps> = ({ run }) => {
  const [activeTab, setActiveTab] = useState<'readable' | 'structured'>('readable');
  const [mdContent, setMdContent] = useState<string>('');
  const [jsonContent, setJsonContent] = useState<string>('');
  const [isLoadingPreview, setIsLoadingPreview] = useState<boolean>(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Parity line info
  const decisionsCount = run.exportParity?.decisions ?? run.record?.decisions?.length ?? 0;
  const tasksCount = run.exportParity?.tasks ?? run.record?.action_items?.length ?? 0;
  const parityOk = run.exportParity ? run.exportParity.ok : true;

  // Fetch preview text on demand without render loop
  useEffect(() => {
    let cancelled = false;

    async function loadPreview() {
      if (!run.id) return;
      setIsLoadingPreview(true);
      setPreviewError(null);

      try {
        if (activeTab === 'readable') {
          if (!mdContent) {
            const res = await fetch(getExportUrl(run.id, 'meeting_record.md'));
            if (!res.ok) throw new Error('Markdown export not ready');
            const text = await res.text();
            if (!cancelled) setMdContent(text);
          }
        } else {
          if (!jsonContent) {
            if (run.record && Object.keys(run.record).length > 0) {
              setJsonContent(JSON.stringify(run.record, null, 2));
            } else {
              const res = await fetch(getExportUrl(run.id, 'meeting_record.json'));
              if (!res.ok) throw new Error('JSON export not ready');
              const text = await res.text();
              if (!cancelled) setJsonContent(text);
            }
          }
        }
      } catch (err: any) {
        if (!cancelled) {
          setPreviewError(err?.message || 'Could not load preview');
        }
      } finally {
        if (!cancelled) {
          setIsLoadingPreview(false);
        }
      }
    }

    loadPreview();

    return () => {
      cancelled = true;
    };
  }, [run.id, activeTab, mdContent, jsonContent, run.record]);

  return (
    <section
      id="section-export"
      style={{
        marginTop: 'var(--s6)',
        paddingTop: 'var(--s5)',
        borderTop: '1px solid var(--rule)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--s3)',
          marginBottom: 'var(--s4)',
        }}
      >
        <div>
          <h3
            style={{
              fontFamily: 'var(--font-doc)',
              fontSize: 'var(--t-lg)',
              fontWeight: 600,
              color: 'var(--ink)',
              marginBottom: '4px',
            }}
          >
            Export Deliverables
          </h3>
          <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--t-xs)' }}>
            All deliverables are derived from the single verified meeting record.
          </p>
        </div>

        {/* Primary Download Everything ZIP Button */}
        <a
          href={getExportUrl(run.id, 'bundle.zip')}
          download="bundle.zip"
          className="chip-pill"
          style={{
            background: 'var(--blue)',
            color: '#FFFFFF',
            border: 'none',
            padding: '8px 16px',
            borderRadius: 'var(--r-ctl)',
            fontSize: 'var(--t-sm)',
            fontWeight: 600,
            textDecoration: 'none',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <Archive size={16} />
          <span>Download everything (.zip)</span>
        </a>
      </div>

      {/* Parity Line */}
      <div
        role="status"
        aria-label="Export parity assertion"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--s2)',
          padding: '8px var(--s3)',
          borderRadius: 'var(--r-ctl)',
          background: parityOk ? 'var(--paper)' : 'var(--alert-wash)',
          border: `1px solid ${parityOk ? 'var(--rule)' : 'var(--alert)'}`,
          marginBottom: 'var(--s4)',
          fontSize: 'var(--t-xs)',
          color: parityOk ? 'var(--ink)' : 'var(--alert)',
        }}
      >
        {parityOk ? (
          <>
            <CheckCircle2 size={16} color="var(--ok)" style={{ flexShrink: 0 }} />
            <span>
              Markdown and JSON contain the same {decisionsCount} {decisionsCount === 1 ? 'decision' : 'decisions'} and {tasksCount} {tasksCount === 1 ? 'task' : 'tasks'}
            </span>
          </>
        ) : (
          <>
            <AlertTriangle size={16} color="var(--alert)" style={{ flexShrink: 0 }} />
            <span style={{ fontWeight: 600 }}>
              Parity discrepancy detected: Markdown and JSON differ ({decisionsCount} decisions, {tasksCount} tasks).
            </span>
          </>
        )}
      </div>

      {/* Ruled List of Files */}
      <div
        className="sheet"
        style={{
          overflow: 'hidden',
          marginBottom: 'var(--s5)',
        }}
      >
        {EXPORT_FILES.map((f, i) => (
          <div
            key={f.name}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px var(--s4)',
              borderBottom: i < EXPORT_FILES.length - 1 ? '1px solid var(--rule)' : 'none',
              gap: 'var(--s3)',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--s3)', minWidth: 0, flex: 1 }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: f.format === 'ZIP' ? 'var(--blue-wash)' : 'var(--paper)',
                  color: f.format === 'ZIP' ? 'var(--blue)' : 'var(--ink-soft)',
                  border: '1px solid var(--rule)',
                  letterSpacing: '0.04em',
                  flexShrink: 0,
                }}
              >
                {f.format}
              </span>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontFamily: 'monospace',
                    fontSize: 'var(--t-xs)',
                    fontWeight: 600,
                    color: 'var(--ink)',
                  }}
                >
                  {f.name}
                </div>
                <div style={{ fontSize: '11.5px', color: 'var(--ink-soft)' }}>
                  {f.desc}
                </div>
              </div>
            </div>

            <a
              href={getExportUrl(run.id, f.name)}
              download={f.name}
              title={`Download ${f.name}`}
              className="player-btn"
              style={{
                textDecoration: 'none',
                width: '32px',
                height: '32px',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              <Download size={14} />
            </a>
          </div>
        ))}
      </div>

      {/* Previews: Readable (Rendered Markdown) & Structured (JSON) */}
      <div style={{ marginTop: 'var(--s5)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--s2)',
          }}
        >
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              type="button"
              onClick={() => setActiveTab('readable')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: 'var(--r-ctl)',
                border: '1px solid',
                borderColor: activeTab === 'readable' ? 'var(--blue)' : 'var(--rule)',
                background: activeTab === 'readable' ? 'var(--blue-wash)' : 'var(--sheet)',
                color: activeTab === 'readable' ? 'var(--blue)' : 'var(--ink-soft)',
                fontWeight: activeTab === 'readable' ? 700 : 500,
                fontSize: 'var(--t-xs)',
                cursor: 'pointer',
              }}
            >
              <Eye size={13} />
              <span>Readable (Markdown)</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab('structured')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                borderRadius: 'var(--r-ctl)',
                border: '1px solid',
                borderColor: activeTab === 'structured' ? 'var(--blue)' : 'var(--rule)',
                background: activeTab === 'structured' ? 'var(--blue-wash)' : 'var(--sheet)',
                color: activeTab === 'structured' ? 'var(--blue)' : 'var(--ink-soft)',
                fontWeight: activeTab === 'structured' ? 700 : 500,
                fontSize: 'var(--t-xs)',
                cursor: 'pointer',
              }}
            >
              <Code2 size={13} />
              <span>Structured (JSON)</span>
            </button>
          </div>

          <span style={{ fontSize: '11px', color: 'var(--ink-soft)' }}>
            Live preview of generated export
          </span>
        </div>

        <div
          className="sheet"
          style={{
            maxHeight: '400px',
            overflowY: 'auto',
            padding: 'var(--s4)',
            background: 'var(--paper)',
            fontSize: 'var(--t-xs)',
            lineHeight: 1.5,
          }}
        >
          {isLoadingPreview ? (
            <div style={{ color: 'var(--ink-soft)', fontStyle: 'italic', padding: 'var(--s4)', textAlign: 'center' }}>
              Loading preview…
            </div>
          ) : previewError ? (
            <div style={{ color: 'var(--alert)', padding: 'var(--s2)' }}>
              {previewError}
            </div>
          ) : activeTab === 'readable' ? (
            <pre
              style={{
                fontFamily: 'var(--font-doc)',
                fontSize: '13.5px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: 'var(--ink)',
                margin: 0,
              }}
            >
              {mdContent || 'No Markdown preview available.'}
            </pre>
          ) : (
            <pre
              style={{
                fontFamily: 'monospace',
                fontSize: '12px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: 'var(--ink)',
                margin: 0,
              }}
            >
              {jsonContent || 'No JSON preview available.'}
            </pre>
          )}
        </div>
      </div>
    </section>
  );
};
