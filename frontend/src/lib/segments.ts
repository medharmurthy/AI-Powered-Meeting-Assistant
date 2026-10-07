import type { Segment } from '../api/types';

/**
 * Format seconds into standard MM:SS string with tabular numbers.
 */
export function formatTime(seconds: number): string {
  if (seconds == null || isNaN(seconds) || seconds < 0) {
    return '00:00';
  }
  const totalSec = Math.floor(seconds);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  const mStr = m.toString().padStart(2, '0');
  const sStr = s.toString().padStart(2, '0');
  return `${mStr}:${sStr}`;
}

/**
 * Format bytes into human-readable size (e.g. '12.4 MB').
 */
export function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Compute bounding [minStart, maxEnd] time range for an array of cited segment IDs.
 */
export function rangeFor(ids: number[], segments: Segment[] = []): [number, number] | null {
  if (!ids || ids.length === 0 || !segments || segments.length === 0) return null;
  const matched = segments.filter((s) => ids.includes(s.id));
  if (matched.length === 0) return null;

  let minStart = Infinity;
  let maxEnd = -Infinity;
  for (const s of matched) {
    if (s.start < minStart) minStart = s.start;
    if (s.end > maxEnd) maxEnd = s.end;
  }
  return [minStart, maxEnd];
}

/**
 * Binary search to find segment covering the given playback time.
 */
export function segmentAt(time: number, segments: Segment[] = []): Segment | null {
  if (!segments || segments.length === 0) return null;

  let low = 0;
  let high = segments.length - 1;

  while (low <= high) {
    const mid = Math.floor((low + high) / 2);
    const seg = segments[mid];
    if (time >= seg.start && time <= seg.end) {
      return seg;
    }
    if (time < seg.start) {
      high = mid - 1;
    } else {
      low = mid + 1;
    }
  }

  return segments.find((s) => time >= s.start && time <= s.end) || null;
}
