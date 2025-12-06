/**
 * FileEditor - Monaco editor component for editing DBT schema and macro files
 */

import { useState } from 'react';
import Editor from '@monaco-editor/react';
import { FileText, Maximize2 } from 'lucide-react';

interface FileEditorProps {
  filename: string;
  content: string;
  language: 'yaml' | 'sql';
  onSave: (content: string) => Promise<void>;
  onCancel: () => void;
  onFullscreen?: () => void;
  isFullscreen?: boolean;
}

export function FileEditor({
  filename,
  content,
  language,
  onSave,
  onCancel,
  onFullscreen,
  isFullscreen = false
}: FileEditorProps) {
  const [editorContent, setEditorContent] = useState(content);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      await onSave(editorContent);
      setIsDirty(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (value: string | undefined) => {
    if (value !== undefined) {
      setEditorContent(value);
      setIsDirty(value !== content);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header with filename and action buttons */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-muted/20">
        <div className="flex items-center gap-2">
          <FileText size={16} />
          <span className="text-sm font-medium">{filename}</span>
          {isDirty && <span className="text-xs text-muted-foreground">(unsaved)</span>}
        </div>
        <div className="flex items-center gap-2">
          {onFullscreen && !isFullscreen && (
            <button
              onClick={onFullscreen}
              className="p-1 hover:bg-accent rounded"
              title="Fullscreen mode"
            >
              <Maximize2 size={16} />
            </button>
          )}
          <button
            onClick={onCancel}
            className="px-3 py-1 text-sm hover:bg-accent rounded transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!isDirty || isSaving}
            className="px-3 py-1 text-sm bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="px-3 py-2 bg-red-50 text-red-600 text-sm border-b border-red-200">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Monaco Editor */}
      <div className="flex-1 overflow-hidden">
        <Editor
          language={language}
          value={editorContent}
          onChange={handleChange}
          options={{
            minimap: { enabled: isFullscreen },
            fontSize: 13,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            wordWrap: isFullscreen ? 'off' : 'on',
            theme: 'vs-light',
            tabSize: 2,
            insertSpaces: true,
          }}
        />
      </div>
    </div>
  );
}
