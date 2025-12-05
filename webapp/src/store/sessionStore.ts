/**
 * Zustand store for SQLBot session state
 */

import { create } from 'zustand';
import type { Session, SessionDetail, Query, Message } from '../lib/types';
import { api } from '../lib/api';

interface SessionStore {
  // Current state
  sessions: Session[];
  currentSession: SessionDetail | null;
  messages: Message[];
  queries: Query[];
  selectedQueryId: string | null;
  isThinking: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  executeQuery: (query: string) => Promise<void>;
  selectQuery: (queryId: string) => void;

  // SSE event handlers
  handleMessage: (message: Message) => void;
  handleQueryComplete: (query: Query) => void;
  handleThinkingStart: () => void;
  handleThinkingEnd: () => void;

  // Reset
  reset: () => void;
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  // Initial state
  sessions: [],
  currentSession: null,
  messages: [],
  queries: [],
  selectedQueryId: null,
  isThinking: false,
  isLoading: false,
  error: null,

  // Load all sessions
  loadSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const sessions = await api.sessions.list();
      set({ sessions, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // Create new session
  createSession: async () => {
    set({ isLoading: true, error: null });
    try {
      const session = await api.sessions.create();

      // Load the new session immediately
      await get().loadSession(session.session_id);

      // Refresh sessions list
      await get().loadSessions();
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // Load existing session
  loadSession: async (sessionId: string) => {
    set({ isLoading: true, error: null });
    try {
      const response: any = await api.sessions.load(sessionId);

      // Flatten the response structure - API returns {session: {...}, queries: [...], conversation_history: {...}}
      const sessionDetail: SessionDetail = {
        ...response.session,
        queries: response.queries,
        conversation_history: response.conversation_history,
        config: {
          safeguard_mode: response.session.safeguard_mode,
          preview_mode: response.session.preview_mode,
          profile: response.session.profile,
        }
      };

      // Convert conversation history to messages
      const messages: Message[] = sessionDetail.conversation_history.messages.map((msg) => {
        let role: 'user' | 'assistant' | 'system' = 'assistant';
        if (msg.type === 'HumanMessage') {
          role = 'user';
        } else if (msg.type === 'SystemMessage') {
          role = 'system';
        }
        return {
          role,
          content: msg.content,
        };
      });

      set({
        currentSession: sessionDetail,
        queries: sessionDetail.queries,
        messages,
        isLoading: false,
        selectedQueryId: null,
      });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // Delete session
  deleteSession: async (sessionId: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.sessions.delete(sessionId);

      // Clear current session if it was deleted
      const current = get().currentSession;
      if (current && current.session_id === sessionId) {
        set({ currentSession: null, messages: [], queries: [], selectedQueryId: null });
      }

      // Refresh sessions list
      await get().loadSessions();
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  // Execute query
  executeQuery: async (query: string) => {
    set({ error: null });
    try {
      // Send query to backend (results will come via SSE)
      await api.query.execute(query);
    } catch (error) {
      set({ error: (error as Error).message });
    }
  },

  // Select query
  selectQuery: (queryId: string) => {
    set({ selectedQueryId: queryId });
  },

  // Handle message from SSE
  handleMessage: (message: Message) => {
    set((state) => ({
      messages: [...state.messages, message],
    }));
  },

  // Handle query complete from SSE
  handleQueryComplete: (query: Query) => {
    set((state) => ({
      queries: [...state.queries, query],
    }));
  },

  // Handle thinking start
  handleThinkingStart: () => {
    set({ isThinking: true });
  },

  // Handle thinking end
  handleThinkingEnd: () => {
    set({ isThinking: false });
  },

  // Reset state
  reset: () => {
    set({
      currentSession: null,
      messages: [],
      queries: [],
      selectedQueryId: null,
      isThinking: false,
      error: null,
    });
  },
}));
