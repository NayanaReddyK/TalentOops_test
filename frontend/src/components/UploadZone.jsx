import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, X } from 'lucide-react';

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export default function UploadZone({ onFileSelect }) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFile = useCallback(
    (file) => {
      setError(null);

      if (file.type !== 'application/pdf') {
        setError('Only PDF files are accepted.');
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        setError('File must be under 10 MB.');
        return;
      }

      setSelectedFile(file);
      onFileSelect?.(file);
    },
    [onFileSelect],
  );

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.[0]) {
        handleFile(e.dataTransfer.files[0]);
      }
    },
    [handleFile],
  );

  const handleChange = useCallback(
    (e) => {
      e.preventDefault();
      if (e.target.files?.[0]) {
        handleFile(e.target.files[0]);
      }
    },
    [handleFile],
  );

  const removeFile = useCallback(
    (e) => {
      e.stopPropagation();
      setSelectedFile(null);
      setError(null);
      onFileSelect?.(null);
      // Reset the input so re-selecting the same file triggers onChange
      if (inputRef.current) inputRef.current.value = '';
    },
    [onFileSelect],
  );

  return (
    <div className="card p-6 animate-fade-in">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        onChange={handleChange}
        className="hidden"
      />

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => !selectedFile && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !selectedFile) {
            inputRef.current?.click();
          }
        }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={[
          'relative flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 transition-all duration-200 outline-none',
          selectedFile
            ? 'cursor-default border-[var(--color-glass-border-strong)] bg-[var(--color-glass-base)]'
            : 'cursor-pointer',
          !selectedFile && dragActive
            ? 'border-[var(--color-accent)] bg-[var(--color-accent-muted)]'
            : '',
          !selectedFile && !dragActive
            ? 'border-[var(--color-glass-border)] hover:border-[var(--color-glass-border-strong)] hover:bg-[var(--color-glass-hover)]'
            : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {!selectedFile ? (
          /* ── Empty state ──────────────────────────────────────────── */
          <>
            <div
              className={[
                'flex h-12 w-12 items-center justify-center rounded-xl transition-colors duration-200',
                dragActive
                  ? 'bg-[var(--color-accent-muted)] text-[var(--color-accent)]'
                  : 'bg-[var(--color-glass-hover)] text-[var(--color-text-muted)]',
              ].join(' ')}
            >
              <Upload className="h-6 w-6" />
            </div>

            <div className="text-center">
              <p className="text-sm font-medium text-[var(--color-text-primary)]">
                Drop your resume here
              </p>
              <p className="mt-1 text-xs text-[var(--color-text-muted)]">
                PDF files only · Max 10 MB
              </p>
            </div>
          </>
        ) : (
          /* ── File selected state ──────────────────────────────────── */
          <div className="flex w-full items-center gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-accent-muted)]">
              <FileText className="h-5 w-5 text-[var(--color-accent)]" />
            </div>

            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-[var(--color-text-primary)]">
                {selectedFile.name}
              </p>
              <p className="text-xs font-mono text-[var(--color-text-muted)]">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>

            <button
              type="button"
              onClick={removeFile}
              className="btn btn-ghost btn-sm gap-1 text-[var(--color-rose)] hover:bg-[var(--color-rose-muted)]"
            >
              <X className="h-3.5 w-3.5" />
              Remove
            </button>
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <p className="mt-3 flex items-center gap-1.5 text-xs font-medium text-[var(--color-rose)]">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-rose)]" />
          {error}
        </p>
      )}
    </div>
  );
}
