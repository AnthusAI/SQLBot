/**
 * Mac-style Menu Bar component (based on DeckBot design)
 */

import { useSessionStore } from '../../store/sessionStore';
import { FileText, FolderOpen, XCircle, Info, Settings } from 'lucide-react';

interface MenuBarProps {
  onOpenPreferences: () => void;
}

export function MenuBar({ onOpenPreferences }: MenuBarProps) {
  const { currentSession, reset } = useSessionStore();
  const hasSession = Boolean(currentSession);

  const handleNewSession = () => {
    useSessionStore.getState().createSession();
  };

  const handleOpenSession = () => {
    // Close current session to show session grid
    reset();
  };

  const handleCloseSession = () => {
    if (confirm('Are you sure you want to close the current session?')) {
      reset();
    }
  };

  const handleAbout = () => {
    alert('SQLBot v2.0\n\nAn AI-powered database query assistant.');
  };

  return (
    <div className="menu-bar !px-3">
      <div className="menu-left">
        {/* App Menu */}
        <div className="menu-item">
          <button className="menu-button">SQLBot</button>
          <div className="dropdown-menu">
            <button onClick={handleAbout} className="dropdown-item">
              <Info size={16} />
              About SQLBot
            </button>
            <div className="dropdown-divider"></div>
            <button onClick={onOpenPreferences} className="dropdown-item">
              <Settings size={16} />
              Preferences...
              <span className="kbd">⌘,</span>
            </button>
          </div>
        </div>

        {/* File Menu - changes based on whether a session is open */}
        <div className="menu-item">
          <button className="menu-button">File</button>
          <div className="dropdown-menu">
            <button onClick={handleNewSession} className="dropdown-item">
              <FileText size={16} />
              New Session
            </button>
            <button onClick={handleOpenSession} className="dropdown-item">
              <FolderOpen size={16} />
              Open Session...
            </button>
            {hasSession && (
              <>
                <div className="dropdown-divider"></div>
                <button onClick={handleCloseSession} className="dropdown-item">
                  <XCircle size={16} />
                  Close Session
                </button>
              </>
            )}
          </div>
        </div>

        {/* View Menu - only shows when session is open */}
        {hasSession && (
          <div className="menu-item">
            <button className="menu-button">View</button>
            <div className="dropdown-menu">
              <button className="dropdown-item checkable active">
                <FileText size={16} />
                Query History
                <span className="kbd">⌘1</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
