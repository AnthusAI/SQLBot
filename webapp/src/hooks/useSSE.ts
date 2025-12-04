/**
 * React hook for Server-Sent Events (SSE) connection
 */

import { useEffect, useRef, useCallback } from 'react';
import type { SSEEventType } from '../lib/types';

export interface SSEEventHandler {
  (eventType: SSEEventType, data: any): void;
}

export function useSSE(onEvent: SSEEventHandler) {
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Create new EventSource connection
    const eventSource = new EventSource('/events');
    eventSourceRef.current = eventSource;

    // Handle connection open
    eventSource.onopen = () => {
      console.log('SSE connection established');
    };

    // Handle errors
    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      // EventSource will automatically try to reconnect
    };

    // Register event listeners for all event types
    const eventTypes: SSEEventType[] = [
      'connected',
      'message',
      'thinking_start',
      'thinking_end',
      'tool_start',
      'tool_end',
      'query_started',
      'query_complete',
      'error',
    ];

    eventTypes.forEach((eventType) => {
      eventSource.addEventListener(eventType, (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          onEvent(eventType, data);
        } catch (error) {
          console.error(`Failed to parse ${eventType} event:`, error);
        }
      });
    });

    return eventSource;
  }, [onEvent]);

  useEffect(() => {
    const eventSource = connect();

    // Cleanup on unmount
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [connect]);

  return {
    reconnect: connect,
  };
}
