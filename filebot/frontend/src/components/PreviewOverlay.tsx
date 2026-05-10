import React, { useEffect, useCallback } from 'react';

interface PreviewOverlayProps {
  url: string | null;
  title?: string;
  onClose: () => void;
}

/**
 * PreviewOverlay - Lightbox-style modal for document preview
 *
 * Renders a fullscreen overlay with the document preview URL in an iframe.
 * Close button / backdrop click / Escape key dismisses the overlay.
 */
const PreviewOverlay: React.FC<PreviewOverlayProps> = ({ url, title, onClose }) => {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && url) {
      onClose();
    }
  }, [url, onClose]);

  useEffect(() => {
    if (url) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [url, handleKeyDown]);

  if (!url) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        zIndex: 999999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        style={{
          position: 'relative',
          width: '90%',
          height: '90%',
          backgroundColor: '#fff',
          borderRadius: '4px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header bar */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '8px 16px',
            borderBottom: '1px solid #ddd',
            backgroundColor: '#f5f5f5',
            borderRadius: '4px 4px 0 0',
          }}
        >
          <span style={{ fontWeight: 600, fontSize: '14px', color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {title || 'Document Preview'}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '22px',
              cursor: 'pointer',
              color: '#666',
              padding: '0 4px',
              lineHeight: 1,
              flexShrink: 0,
            }}
            title="Close (Esc)"
          >
            &times;
          </button>
        </div>
        {/* Iframe content */}
        <iframe
          src={url}
          style={{
            flex: 1,
            width: '100%',
            border: 'none',
          }}
          title={title || 'Document Preview'}
        />
      </div>
    </div>
  );
};

export default PreviewOverlay;
