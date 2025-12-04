/**
 * Resizable divider component for split panels
 */

import { useEffect, useRef } from 'react';

interface ResizerProps {
  onResize: (width: number) => void;
  minWidth?: number;
  maxWidth?: number;
}

export function Resizer({ onResize, minWidth = 300, maxWidth = 800 }: ResizerProps) {
  const resizerRef = useRef<HTMLDivElement>(null);
  const isResizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      e.preventDefault();
      isResizingRef.current = true;
      startXRef.current = e.clientX;

      // Get the sidebar element (next sibling)
      const sidebar = resizerRef.current?.nextElementSibling as HTMLElement;
      if (sidebar) {
        startWidthRef.current = sidebar.offsetWidth;
      }

      // Add visual feedback
      resizerRef.current?.classList.add('resizing');
      document.body.style.cursor = 'ew-resize';
      document.body.style.userSelect = 'none';
    };

    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;

      e.preventDefault();

      const dx = startXRef.current - e.clientX; // Reversed because sidebar is on right
      const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidthRef.current + dx));

      onResize(newWidth);
    };

    const handleMouseUp = () => {
      if (isResizingRef.current) {
        isResizingRef.current = false;
        resizerRef.current?.classList.remove('resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    const resizer = resizerRef.current;
    if (resizer) {
      resizer.addEventListener('mousedown', handleMouseDown);
    }

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mouseleave', handleMouseUp);

    return () => {
      if (resizer) {
        resizer.removeEventListener('mousedown', handleMouseDown);
      }
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mouseleave', handleMouseUp);
    };
  }, [onResize, minWidth, maxWidth]);

  return (
    <div
      ref={resizerRef}
      className="resizer"
    />
  );
}
