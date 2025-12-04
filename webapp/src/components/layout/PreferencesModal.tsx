/**
 * Preferences modal component
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentTheme: 'light' | 'dark' | 'system';
  onThemeChange: (theme: 'light' | 'dark' | 'system') => void;
}

export function PreferencesModal({ isOpen, onClose, currentTheme, onThemeChange }: PreferencesModalProps) {
  const [selectedTheme, setSelectedTheme] = useState(currentTheme);

  useEffect(() => {
    setSelectedTheme(currentTheme);
  }, [currentTheme]);

  if (!isOpen) return null;

  const handleSave = () => {
    onThemeChange(selectedTheme);
    onClose();
  };

  const handleCancel = () => {
    setSelectedTheme(currentTheme); // Reset to current value
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 pointer-events-none">
        <div
          className="bg-card border border-border rounded-lg shadow-lg w-full max-w-md pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h2 className="font-semibold">Preferences</h2>
            <button
              onClick={handleCancel}
              className="p-1 hover:bg-accent rounded transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Content */}
          <div className="p-4 space-y-4">
            {/* Theme Setting */}
            <div>
              <label className="block text-sm font-medium mb-2">Theme</label>
              <div className="space-y-2">
                <label className="flex items-center p-2 border border-border rounded hover:bg-muted cursor-pointer">
                  <input
                    type="radio"
                    name="theme"
                    value="light"
                    checked={selectedTheme === 'light'}
                    onChange={(e) => setSelectedTheme(e.target.value as 'light' | 'dark' | 'system')}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">Light</div>
                    <div className="text-xs text-muted-foreground">Always use light theme</div>
                  </div>
                </label>

                <label className="flex items-center p-2 border border-border rounded hover:bg-muted cursor-pointer">
                  <input
                    type="radio"
                    name="theme"
                    value="dark"
                    checked={selectedTheme === 'dark'}
                    onChange={(e) => setSelectedTheme(e.target.value as 'light' | 'dark' | 'system')}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">Dark</div>
                    <div className="text-xs text-muted-foreground">Always use dark theme</div>
                  </div>
                </label>

                <label className="flex items-center p-2 border border-border rounded hover:bg-muted cursor-pointer">
                  <input
                    type="radio"
                    name="theme"
                    value="system"
                    checked={selectedTheme === 'system'}
                    onChange={(e) => setSelectedTheme(e.target.value as 'light' | 'dark' | 'system')}
                    className="mr-3"
                  />
                  <div>
                    <div className="font-medium">System</div>
                    <div className="text-xs text-muted-foreground">Follow system preference</div>
                  </div>
                </label>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-border">
            <button
              onClick={handleCancel}
              className="px-3 py-1.5 border border-border rounded hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-3 py-1.5 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
