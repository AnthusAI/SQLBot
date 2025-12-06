/**
 * FullscreenEditorModal - Fullscreen mode wrapper for FileEditor
 */

import { FileEditor } from './FileEditor';

interface FullscreenEditorModalProps {
  isOpen: boolean;
  filename: string;
  content: string;
  language: 'yaml' | 'sql';
  onSave: (content: string) => Promise<void>;
  onClose: () => void;
}

export function FullscreenEditorModal({
  isOpen,
  filename,
  content,
  language,
  onSave,
  onClose
}: FullscreenEditorModalProps) {
  if (!isOpen) return null;

  const handleSave = async (newContent: string) => {
    await onSave(newContent);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-background">
      <FileEditor
        filename={filename}
        content={content}
        language={language}
        onSave={handleSave}
        onCancel={onClose}
        isFullscreen={true}
      />
    </div>
  );
}
