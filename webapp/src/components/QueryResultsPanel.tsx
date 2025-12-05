/**
 * Query Results Panel - displays DBT query history and results
 * Similar to the textual app's right panel
 */

import { useState, useEffect } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { DataTable } from './chat/DataTable';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface QueryResult {
  index: number;
  timestamp: string;
  query_text: string;
  success: boolean;
  row_count: number | null;
  columns: string[] | null;
  data: Record<string, any>[] | null;
  error: string | null;
  execution_time: number;
}

interface QueryResultsPanelProps {
  onCollapsedChange?: (collapsed: boolean) => void;
}

export function QueryResultsPanel({ onCollapsedChange }: QueryResultsPanelProps) {
  const { currentSession } = useSessionStore();
  const [queryResults, setQueryResults] = useState<QueryResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<QueryResult | null>(null);
  const [activeTab, setActiveTab] = useState<'result' | 'query'>('result');
  const [listWidth, setListWidth] = useState(180); // Query list width
  const [isCollapsed, setIsCollapsed] = useState(true); // Start collapsed
  const [hasInitialized, setHasInitialized] = useState(false); // Track if we've done initial load

  // Notify parent when collapsed state changes
  const handleCollapsedChange = (collapsed: boolean) => {
    setIsCollapsed(collapsed);
    onCollapsedChange?.(collapsed);
  };

  // Notify parent of initial collapsed state
  useEffect(() => {
    onCollapsedChange?.(isCollapsed);
  }, []);

  // Fetch query results when session changes
  useEffect(() => {
    // Reset state when session changes
    setQueryResults([]);
    setSelectedResult(null);
    setHasInitialized(false);

    if (!currentSession) {
      return;
    }

    const fetchResults = async () => {
      try {
        console.log(`[QueryResultsPanel] Fetching results for session: ${currentSession.session_id}`);
        const response = await fetch(`/api/sessions/${currentSession.session_id}/query_results`);

        if (!response.ok) {
          console.error(`Failed to fetch query results: HTTP ${response.status}`);
          return;
        }

        const data = await response.json();
        console.log(`[QueryResultsPanel] Received data:`, data);
        console.log(`[QueryResultsPanel] Results count: ${data.results?.length || 0}`);

        if (data.results) {
          setQueryResults(data.results);
          // Auto-select the most recent result on initial load
          if (data.results.length > 0 && !hasInitialized) {
            console.log(`[QueryResultsPanel] Auto-selecting first result:`, data.results[0]);
            setSelectedResult(data.results[0]);
          }
        }
      } catch (error) {
        console.error('Failed to fetch query results:', error);
        // Don't set error state - just log it and continue polling
      }
    };

    fetchResults();

    // Poll for updates every 2 seconds
    const interval = setInterval(fetchResults, 2000);
    return () => clearInterval(interval);
  }, [currentSession]);

  // Auto-select newest result when results update AND auto-expand ONLY on initial load
  useEffect(() => {
    if (queryResults.length > 0) {
      const newest = queryResults[0];
      // Only update if it's a new result (different index)
      const isNewResult = !selectedResult || selectedResult.index !== newest.index;
      if (isNewResult) {
        setSelectedResult(newest);
      }
      // Auto-expand ONLY on initial load, not on subsequent updates
      if (!hasInitialized && isCollapsed) {
        handleCollapsedChange(false);
        setHasInitialized(true);
      }
    }
  }, [queryResults]);

  const formatTimestamp = (isoString: string) => {
    const date = new Date(isoString);
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const dayName = days[date.getDay()];
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${dayName} ${displayHours}:${minutes} ${ampm}`;
  };

  // Collapsed state - show thin bar with expand button
  if (isCollapsed) {
    return (
      <div className="flex flex-col h-full bg-card">
        {/* Spacer to push button to bottom */}
        <div className="flex-1" />

        {/* Expand button at bottom */}
        <div className="p-2 border-t border-border flex justify-center">
          <button
            onClick={() => handleCollapsedChange(false)}
            className="p-2 hover:bg-accent rounded transition-colors"
            title="Expand query results"
          >
            <ChevronLeft size={20} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left Sidebar - List of queries with collapse button at bottom */}
      <div
        className="border-r border-border flex flex-col"
        style={{ width: `${listWidth}px` }}
      >
        <div className="px-3 py-2 border-b border-border">
          <h3 className="font-semibold text-sm">Query Results</h3>
        </div>
        <div className="flex-1 overflow-y-auto">
          {queryResults.map((result) => (
            <div
              key={result.index}
              onClick={() => setSelectedResult(result)}
              className={`px-3 py-2 cursor-pointer transition-colors border-b border-border/50 ${
                selectedResult?.index === result.index
                  ? 'bg-accent'
                  : 'hover:bg-muted/50'
              }`}
            >
              <div className="text-xs flex items-center gap-2">
                <span className="font-medium">
                  {formatTimestamp(result.timestamp)}
                </span>
                {result.row_count !== null && result.row_count > 0 && (
                  <span className="text-muted-foreground">
                    - {result.row_count} {result.row_count === 1 ? 'row' : 'rows'}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Collapse button at bottom of query list */}
        <div className="p-2 border-t border-border flex justify-start">
          <button
            onClick={() => handleCollapsedChange(true)}
            className="p-2 hover:bg-accent rounded transition-colors"
            title="Collapse query results"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* Custom Resizer for query list (normal left-to-right direction) */}
      <div
        className="resizer"
        onMouseDown={(e) => {
          e.preventDefault();
          const startX = e.clientX;
          const startWidth = listWidth;

          const handleMouseMove = (e: MouseEvent) => {
            const dx = e.clientX - startX; // Normal direction (not reversed)
            const newWidth = Math.max(150, Math.min(500, startWidth + dx));
            setListWidth(newWidth);
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
        }}
      />

      {/* Right Content - Selected query details */}
      {selectedResult ? (
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-border">
            <button
              onClick={() => setActiveTab('query')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'query'
                  ? 'border-b-2 border-primary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Query
            </button>
            <button
              onClick={() => setActiveTab('result')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'result'
                  ? 'border-b-2 border-primary text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Result
            </button>
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-auto">
            {activeTab === 'result' ? (
              <div className="p-3 overflow-x-auto overflow-y-auto">
                {selectedResult.success && selectedResult.data && selectedResult.columns ? (
                  <DataTable
                    columns={selectedResult.columns}
                    rows={selectedResult.data.map(row =>
                      selectedResult.columns!.map(col => row[col])
                    )}
                    sessionId={currentSession?.session_id}
                    queryIndex={selectedResult.index}
                  />
                ) : selectedResult.error ? (
                  <div className="text-sm text-destructive p-2 bg-destructive/10 rounded">
                    <p className="font-semibold">Error:</p>
                    <p className="mt-1">{selectedResult.error}</p>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No data returned</p>
                )}
              </div>
            ) : (
              <div className="p-3 overflow-x-auto">
                <pre className="text-xs font-mono bg-muted/30 p-3 rounded whitespace-pre">
                  {selectedResult.query_text}
                </pre>
                {selectedResult.execution_time && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Executed in {selectedResult.execution_time.toFixed(2)}s
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
