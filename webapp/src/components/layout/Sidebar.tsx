/**
 * Resizable sidebar component with session list
 */

import { useState } from 'react';
import { useSessionStore } from '../../store/sessionStore';
import { ChevronLeft, ChevronRight, Sun, Moon, Monitor, FilePlus } from 'lucide-react';

interface SidebarProps {
  theme: 'light' | 'dark' | 'system';
  onThemeChange: (theme: 'light' | 'dark' | 'system') => void;
}

export function Sidebar({ theme, onThemeChange }: SidebarProps) {
  const { sessions, currentSession, createSession, loadSession } = useSessionStore();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [width, setWidth] = useState(256); // Default 256px (w-64)

  const handleResize = (e: React.MouseEvent) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startX;
      const newWidth = Math.max(200, Math.min(400, startWidth + delta));
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
  };

  const cycleTheme = () => {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    const nextTheme = themes[(currentIndex + 1) % themes.length];
    onThemeChange(nextTheme);
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun size={20} />;
      case 'dark':
        return <Moon size={20} />;
      case 'system':
        return <Monitor size={20} />;
    }
  };

  if (isCollapsed) {
    return (
      <div className="flex flex-col bg-card border-r border-border" style={{ width: '48px' }}>
        {/* Spacer to push controls to bottom */}
        <div className="flex-1" />

        {/* Footer with controls */}
        <div className="p-2 border-t border-border flex flex-col items-center gap-2">
          <button
            onClick={cycleTheme}
            className="p-2 hover:bg-accent rounded transition-colors"
            title={`Theme: ${theme}`}
          >
            {getThemeIcon()}
          </button>
          <button
            onClick={() => setIsCollapsed(false)}
            className="p-2 hover:bg-accent rounded transition-colors"
            title="Expand sidebar"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col bg-card border-r border-border" style={{ width: `${width}px` }}>
        {/* Session list */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-3 py-2 space-y-2">
            {/* New Session card */}
            <div
              onClick={() => createSession()}
              className="px-2 py-1 rounded cursor-pointer transition-colors hover:bg-muted flex items-center gap-2"
            >
              <FilePlus size={16} />
              <span className="text-sm font-medium">New Session</span>
            </div>

            {/* Existing sessions */}
            {sessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => loadSession(session.session_id)}
                className={`px-2 py-1 rounded cursor-pointer transition-colors ${
                  currentSession?.session_id === session.session_id
                    ? 'bg-accent'
                    : 'hover:bg-muted'
                }`}
              >
                <div className="text-sm font-medium truncate">{session.name}</div>
                <div className="text-xs text-muted-foreground">
                  {session.query_count || 0} queries
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer with controls */}
        <div className="p-2 border-t border-border flex items-center justify-between">
          <button
            onClick={cycleTheme}
            className="p-2 hover:bg-accent rounded transition-colors"
            title={`Theme: ${theme}`}
          >
            {getThemeIcon()}
          </button>
          <button
            onClick={() => setIsCollapsed(true)}
            className="p-2 hover:bg-accent rounded transition-colors"
            title="Collapse sidebar"
          >
            <ChevronLeft size={20} />
          </button>
        </div>
      </div>

      {/* Resizer */}
      <div
        className="resizer"
        onMouseDown={handleResize}
      />
    </>
  );
}
