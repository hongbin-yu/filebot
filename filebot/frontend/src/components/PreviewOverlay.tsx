import React, { useEffect, useCallback, useState, useRef } from 'react';

interface PreviewOverlayProps {
  url: string | null;
  title?: string;
  fileType?: string;
  onClose: () => void;
}

/** Check if the file type is an image (non-PDF, non-HTML) */
const isImageType = (fileType?: string): boolean => {
  if (!fileType) return false;
  const ft = fileType.toLowerCase();
  // tiff/tif handled separately (converted to PDF), not rendered as <img>
  if (ft.match(/tiff?/)) return false;
  return /(jpe?g|png|gif|bmp|webp|svg)/.test(ft) && !ft.match(/html?/);
};

/** Check if the file type is a video */
const isVideoType = (fileType?: string): boolean => {
  if (!fileType) return false;
  return fileType.toLowerCase() === 'video';
};

/**
 * PreviewOverlay - Lightbox-style modal for document preview
 *
 * Images: displayed with <img> that fits the screen initially;
 *          click to toggle between fit-to-screen and full-size.
 * Other: rendered in an iframe (PDF, HTML, etc.)
 * Close button / backdrop click / Escape key dismisses the overlay.
 */
const PreviewOverlay: React.FC<PreviewOverlayProps> = ({ url, title, fileType, onClose }) => {
  const [zoomed, setZoomed] = useState(false);
  const zoomedRef = useRef(zoomed);
  zoomedRef.current = zoomed;

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && url) {
      if (zoomedRef.current) {
        setZoomed(false);
      } else {
        onClose();
      }
    }
  }, [url, onClose]);

  useEffect(() => {
    if (url) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
      setZoomed(false);
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [url, handleKeyDown]);

  if (!url) return null;

  const imagePreview = isImageType(fileType) || !!(url.match(/\.(jpe?g|png|gif|bmp|webp|svg)(\?|$)/i));
  const videoPreview = isVideoType(fileType);

  // Derive thumbnail URL for video poster (replace download?preview=1 with thumbnail?)
  const videoPoster = videoPreview ? url.replace(/\/download\?preview=1&/, '/thumbnail?') : undefined;

  const isMedia = imagePreview || videoPreview;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        zIndex: 999999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
      onClick={isMedia && zoomed ? () => setZoomed(false) : onClose}
    >
      <div
        style={{
          position: 'relative',
          width: isMedia && zoomed ? 'auto' : '90%',
          height: isMedia && zoomed ? 'auto' : '90%',
          maxWidth: isMedia ? '90vw' : '600px',
          maxHeight: '90vh',
          backgroundColor: isMedia ? 'transparent' : '#fff',
          borderRadius: isMedia ? '0' : '4px',
          boxShadow: isMedia ? 'none' : '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          overflow: isMedia ? 'auto' : 'hidden',
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
            borderBottom: isMedia ? 'none' : '1px solid #ddd',
            backgroundColor: isMedia ? 'rgba(0,0,0,0.5)' : '#f5f5f5',
            borderRadius: isMedia ? '0' : '4px 4px 0 0',
            color: isMedia ? '#fff' : '#333',
            flexShrink: 0,
          }}
        >
          <span style={{ fontWeight: 600, fontSize: '14px', color: isMedia ? '#fff' : '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {title || 'Document Preview'}
            {imagePreview && <span style={{ marginLeft: 8, fontSize: 11, opacity: 0.7 }}>{zoomed ? '(click to fit)' : '(click to zoom)'}</span>}
          </span>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '22px',
              cursor: 'pointer',
              color: isMedia ? '#fff' : '#666',
              padding: '0 4px',
              lineHeight: 1,
              flexShrink: 0,
            }}
            title="Close (Esc)"
          >
            &times;
          </button>
        </div>
        {/* Content */}
        {imagePreview ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: zoomed ? 'flex-start' : 'center',
              justifyContent: zoomed ? 'flex-start' : 'center',
              overflow: zoomed ? 'auto' : 'hidden',
              minHeight: 0,
            }}
          >
            <img
              src={url}
              alt={title || 'Preview'}
              onClick={() => setZoomed(!zoomed)}
              style={{
                maxWidth: zoomed ? 'none' : '100%',
                maxHeight: zoomed ? 'none' : '90vh',
                cursor: zoomed ? 'zoom-out' : 'zoom-in',
                userSelect: 'none',
                display: 'block',
              }}
              draggable={false}
            />
          </div>
        ) : videoPreview ? (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 0,
              padding: '16px',
            }}
          >
            <video
              controls
              poster={videoPoster}
              style={{
                maxWidth: '100%',
                maxHeight: '70vh',
                borderRadius: '4px',
                outline: 'none',
              }}
              src={url}
            >
              Your browser does not support the video tag.
            </video>
          </div>
        ) : (
          <iframe
            src={url}
            style={{
              flex: 1,
              width: '100%',
              border: 'none',
            }}
            title={title || 'Document Preview'}
          />
        )}
      </div>
    </div>
  );
};

export default PreviewOverlay;
