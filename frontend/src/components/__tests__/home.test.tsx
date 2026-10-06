import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChipInput } from '../home/ChipInput';
import { DropStage } from '../home/DropStage';
import { HealthList } from '../home/HealthList';
import type { AppError } from '../../api/types';

describe('Home Components', () => {
  describe('ChipInput', () => {
    it('renders initial chips and adds a new chip on Enter', () => {
      const handleChange = vi.fn();
      render(
        <ChipInput
          label="Terms to listen for"
          chips={['Kubernetes', 'OAuth']}
          onChange={handleChange}
        />
      );

      expect(screen.getByText('Kubernetes')).toBeDefined();
      expect(screen.getByText('OAuth')).toBeDefined();

      const input = screen.getByRole('textbox');
      fireEvent.change(input, { target: { value: 'Redis' } });
      fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

      expect(handleChange).toHaveBeenCalledWith(['Kubernetes', 'OAuth', 'Redis']);
    });

    it('removes a chip when delete button is clicked', () => {
      const handleChange = vi.fn();
      render(
        <ChipInput
          label="Participants"
          chips={['Priya', 'Dan']}
          onChange={handleChange}
        />
      );

      const removeBtn = screen.getByLabelText('Remove Priya');
      fireEvent.click(removeBtn);

      expect(handleChange).toHaveBeenCalledWith(['Dan']);
    });
  });

  describe('DropStage Preflight Validation', () => {
    it('rejects unsupported file formats with UNSUPPORTED_TYPE catalogue error', () => {
      const handleFileSelect = vi.fn();
      let errorState: AppError | null = null;
      const setValidationError = vi.fn((err) => {
        errorState = err;
      });

      const { rerender } = render(
        <DropStage
          selectedFile={null}
          duration={null}
          onFileSelect={handleFileSelect}
          validationError={errorState}
          setValidationError={setValidationError}
        />
      );

      const input = screen.getByLabelText('Upload meeting recording').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
      expect(input).toBeDefined();

      const invalidFile = new File(['hello content'], 'notes.txt', { type: 'text/plain' });
      fireEvent.change(input, { target: { files: [invalidFile] } });

      expect(setValidationError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'UNSUPPORTED_TYPE',
          title: "That file type isn't supported",
        })
      );
      expect(handleFileSelect).toHaveBeenCalledWith(null, null);

      // Re-render with validation error
      rerender(
        <DropStage
          selectedFile={null}
          duration={null}
          onFileSelect={handleFileSelect}
          validationError={errorState}
          setValidationError={setValidationError}
        />
      );
      expect(screen.getByText("That file type isn't supported")).toBeDefined();
    });

    it('rejects empty (0 byte) files with EMPTY_FILE catalogue error', () => {
      const handleFileSelect = vi.fn();
      const setValidationError = vi.fn();

      render(
        <DropStage
          selectedFile={null}
          duration={null}
          onFileSelect={handleFileSelect}
          validationError={null}
          setValidationError={setValidationError}
        />
      );

      const input = screen.getByLabelText('Upload meeting recording').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
      const emptyFile = new File([], 'silent.wav', { type: 'audio/wav' });
      fireEvent.change(input, { target: { files: [emptyFile] } });

      expect(setValidationError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'EMPTY_FILE',
          title: 'That file is empty',
        })
      );
      expect(handleFileSelect).toHaveBeenCalledWith(null, null);
    });

    it('rejects files larger than 500 MB with TOO_LARGE error', () => {
      const handleFileSelect = vi.fn();
      const setValidationError = vi.fn();

      render(
        <DropStage
          selectedFile={null}
          duration={null}
          onFileSelect={handleFileSelect}
          validationError={null}
          setValidationError={setValidationError}
        />
      );

      const input = screen.getByLabelText('Upload meeting recording').parentElement?.querySelector('input[type="file"]') as HTMLInputElement;
      const hugeFile = new File(['test'], 'huge.mp3', { type: 'audio/mp3' });
      Object.defineProperty(hugeFile, 'size', { value: 600 * 1024 * 1024 });

      fireEvent.change(input, { target: { files: [hugeFile] } });

      expect(setValidationError).toHaveBeenCalledWith(
        expect.objectContaining({
          code: 'TOO_LARGE',
          title: 'The file is larger than 500 MB',
        })
      );
      expect(handleFileSelect).toHaveBeenCalledWith(null, null);
    });
  });

  describe('HealthList', () => {
    it('renders actionable issues with copyable fix command', () => {
      const issues: AppError[] = [
        {
          code: 'MODEL_MISSING',
          title: 'Model isn’t installed',
          detail: 'gemma3:12b is required',
          fix: 'ollama pull gemma3:12b',
          retryable: true,
        },
      ];

      render(<HealthList issues={issues} />);

      expect(screen.getByText('Model isn’t installed:')).toBeDefined();
      expect(screen.getByText('ollama pull gemma3:12b')).toBeDefined();
      expect(screen.getByTitle('Copy command')).toBeDefined();
    });
  });
});
