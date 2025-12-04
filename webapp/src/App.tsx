/**
 * Main App component for SQLBot web interface
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import { useSessionStore } from './store/sessionStore';
import { useSSE } from './hooks/useSSE';
import { MenuBar } from './components/layout/MenuBar';
import { Sidebar } from './components/layout/Sidebar';
import { Resizer } from './components/layout/Resizer';
import { PreferencesModal } from './components/layout/PreferencesModal';
import { Message, MessageFormatter } from './components/chat';
import type { SSEEventType } from './lib/types';

type Theme = 'light' | 'dark' | 'system';

function App() {
  const {
    loadSessions,
    createSession,
    handleMessage,
    handleQueryComplete,
    handleThinkingStart,
    handleThinkingEnd,
  } = useSessionStore();

  const [theme, setTheme] = useState<Theme>('system');
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false);
  const [introBanner, setIntroBanner] = useState<string>('');

  // Load intro banner on mount
  useEffect(() => {
    fetch('/api/intro')
      .then(res => res.json())
      .then(data => setIntroBanner(data.content))
      .catch(err => console.error('Failed to load intro banner:', err));
  }, []);

  // Load sessions on mount and auto-create if none exist
  useEffect(() => {
    loadSessions().then(() => {
      const store = useSessionStore.getState();
      if (!store.currentSession && store.sessions.length === 0) {
        // Auto-create first session
        createSession();
      }
    });
  }, [loadSessions, createSession]);

  // Load theme from backend
  useEffect(() => {
    fetch('/api/preferences/theme')
      .then(r => r.json())
      .then(data => {
        if (data.value) {
          setTheme(data.value as Theme);
          applyTheme(data.value as Theme, false);
        }
      })
      .catch(() => {
        // Fallback to system theme
        applyTheme('system', false);
      });
  }, []);

  const applyTheme = (newTheme: Theme, saveToBackend = true) => {
    document.documentElement.setAttribute('data-theme', newTheme);
    setTheme(newTheme);

    if (saveToBackend) {
      fetch('/api/preferences/theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: newTheme })
      }).catch(err => console.error('Error saving theme:', err));
    }
  };

  // Handle SSE events - memoized to prevent reconnections
  const handleSSEEvent = useCallback((eventType: SSEEventType, data: any) => {
    console.log('SSE Event:', eventType, data);

    switch (eventType) {
      case 'connected':
        console.log('Connected to SSE');
        break;

      case 'message':
        handleMessage(data);
        break;

      case 'query_complete':
        handleQueryComplete(data);
        break;

      case 'thinking_start':
        handleThinkingStart();
        break;

      case 'thinking_end':
        handleThinkingEnd();
        break;

      case 'error':
        console.error('Server error:', data);
        break;

      default:
        console.log('Unhandled event:', eventType, data);
    }
  }, [handleMessage, handleQueryComplete, handleThinkingStart, handleThinkingEnd]);

  // Connect to SSE
  useSSE(handleSSEEvent);

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-foreground overflow-hidden">
      <MenuBar onOpenPreferences={() => setIsPreferencesOpen(true)} />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar theme={theme} onThemeChange={applyTheme} />
        <SessionView introBanner={introBanner} />
      </div>
      <PreferencesModal
        isOpen={isPreferencesOpen}
        onClose={() => setIsPreferencesOpen(false)}
        currentTheme={theme}
        onThemeChange={applyTheme}
      />
    </div>
  );
}

function SessionView({ introBanner }: { introBanner: string }) {
  const { currentSession, messages, queries, isThinking, executeQuery } = useSessionStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [sidebarWidth, setSidebarWidth] = useState(384); // 96 * 4 = 384px (w-96)

  const handleSubmit = (query: string) => {
    executeQuery(query);
  };

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  if (!currentSession) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <p>Select or create a session from the sidebar</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left panel - Chat */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto overflow-x-hidden">
          {/* Always show banner as first message */}
          {introBanner && (
            <Message role="system" content={<MessageFormatter content={introBanner} role="system" />} />
          )}

          {/* Show conversation messages */}
          {messages.map((msg, i) => (
            <Message
              key={i}
              role={msg.role}
              content={<MessageFormatter content={msg.content} role={msg.role} />}
              timestamp={msg.timestamp}
            />
          ))}

          {/* Thinking indicator */}
          {isThinking && (
            <Message role="system" content="Thinking..." />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-border px-3 py-4">
          <QueryInput onSubmit={handleSubmit} disabled={isThinking} />
        </div>
      </div>

      {/* Resizer */}
      <Resizer onResize={setSidebarWidth} minWidth={300} maxWidth={800} />

      {/* Right panel - Queries */}
      <div
        className="flex flex-col bg-muted/20"
        style={{ width: `${sidebarWidth}px` }}
      >
        <div className="px-3 py-4 border-b border-border">
          <h3 className="font-semibold">Query History</h3>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-2">
          {queries.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No queries yet
            </p>
          ) : (
            queries.map((query) => (
              <div
                key={query.id}
                className="p-3 bg-card rounded-md hover:bg-accent cursor-pointer transition-colors"
              >
                <p className="text-sm font-mono truncate text-card-foreground">{query.user_input}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {new Date(query.timestamp).toLocaleTimeString()}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function QueryInput({ onSubmit, disabled }: { onSubmit: (query: string) => void; disabled: boolean }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const value = e.currentTarget.value.trim();
      if (value) {
        onSubmit(value);
        e.currentTarget.value = '';
        // Reset height
        e.currentTarget.style.height = 'auto';
      }
    }
  };

  // Auto-expand textarea on input
  const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
    const target = e.currentTarget;
    target.style.height = 'auto';
    target.style.height = Math.min(target.scrollHeight, 200) + 'px';
  };

  return (
    <div className="flex gap-2">
      <textarea
        ref={textareaRef}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder=""
        className="flex-1 px-3 py-2 border border-input rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
        rows={1}
      />
      <button
        onClick={() => {
          const textarea = textareaRef.current;
          if (textarea && textarea.value.trim()) {
            onSubmit(textarea.value.trim());
            textarea.value = '';
            // Reset height
            textarea.style.height = 'auto';
          }
        }}
        disabled={disabled}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  );
}

export default App;
