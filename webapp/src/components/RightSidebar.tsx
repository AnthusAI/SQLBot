/**
 * RightSidebar - tabbed sidebar with Profile and Results panels
 */

import { useSessionStore } from '../store/sessionStore';
import { ProfilePanel } from './ProfilePanel';
import { QueryResultsPanel } from './QueryResultsPanel';

interface RightSidebarProps {
  onCollapsedChange: (collapsed: boolean) => void;
}

export function RightSidebar({ onCollapsedChange }: RightSidebarProps) {
  const { currentSession, rightSidebarTab, setRightSidebarTab } = useSessionStore();

  // Show only Profile tab when no session
  const showQueriesTab = currentSession !== null;

  return (
    <div className="flex flex-col h-full bg-card">
      {/* Tab Navigation - ALWAYS show tabs */}
      <div className="flex border-b border-border">
        {showQueriesTab && (
          <button
            onClick={() => setRightSidebarTab('queries')}
            className={`px-4 py-2 text-sm font-medium transition-colors ${
              rightSidebarTab === 'queries'
                ? 'border-b-2 border-primary text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Queries
          </button>
        )}
        <button
          onClick={() => setRightSidebarTab('profile')}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            rightSidebarTab === 'profile'
              ? 'border-b-2 border-primary text-foreground'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Profile
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {rightSidebarTab === 'queries' ? (
          <QueryResultsPanel onCollapsedChange={onCollapsedChange} />
        ) : (
          <ProfilePanel />
        )}
      </div>
    </div>
  );
}
