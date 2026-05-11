import React, { useEffect, useState } from 'react';

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  visible: boolean;
}

let toastIdCounter = 0;
let globalSetToasts: React.Dispatch<React.SetStateAction<Toast[]>> | null = null;

export function showToast(message: string, type: Toast['type'] = 'info', duration = 8000) {
  if (globalSetToasts) {
    const id = ++toastIdCounter;
    globalSetToasts(prev => [...prev, { id, message, type, visible: true }]);
    setTimeout(() => {
      globalSetToasts?.(prev => prev.map(t => t.id === id ? { ...t, visible: false } : t));
      setTimeout(() => {
        globalSetToasts?.(prev => prev.filter(t => t.id !== id));
      }, 300);
    }, duration);
  }
}

const ToastNotification: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    globalSetToasts = setToasts;
    return () => { globalSetToasts = null; };
  }, []);

  const typeStyles: Record<Toast['type'], React.CSSProperties> = {
    success: { backgroundColor: '#278400', borderLeft: '5px solid #1a5e00' },
    error: { backgroundColor: '#d3080c', borderLeft: '5px solid #a00609' },
    warning: { backgroundColor: '#ee8700', borderLeft: '5px solid #b56600' },
    info: { backgroundColor: '#335075', borderLeft: '5px solid #1f3045' }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 20,
      right: 20,
      zIndex: 99999,
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
      pointerEvents: 'none',
    }}>
      {toasts.map(toast => (
        <div
          key={toast.id}
          style={{
            ...typeStyles[toast.type],
            color: '#fff',
            padding: '14px 20px',
            borderRadius: 4,
            minWidth: 280,
            maxWidth: 480,
            boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
            transition: 'opacity 0.3s ease, transform 0.3s ease',
            opacity: toast.visible ? 1 : 0,
            transform: toast.visible ? 'translateX(0)' : 'translateX(50px)',
            pointerEvents: 'auto',
            fontSize: 14,
            lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
          }}
        >
          {toast.message}
        </div>
      ))}
    </div>
  );
};

export default ToastNotification;
