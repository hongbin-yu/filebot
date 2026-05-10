import React, { useEffect, ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

interface ClientLayoutProps {
  children: ReactNode;
}

/**
 * ClientLayout - Client layout component
 *
 * Used for client routes (/apps/*), applying Canada.ca WET/GCWeb theme
 * WET framework automatically injects Canada.ca header/footer (outside React root)
 * On route change, re-triggers WET initialization for new content
 */
const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const location = useLocation();

  useEffect(() => {
    // Re-trigger WET plugin initialization after React renders new content
    // WET scans the DOM for data attributes / classes and enhances elements
    if (typeof $ !== 'undefined' && $.fn && $.fn.trigger) {
      try {
        $(document).trigger('wb-update.wb');
      } catch(e) {
        console.warn('WET re-init failed:', e);
      }
    }
  }, [location.pathname]);

  return (
    <>
      {/* Canada.ca content container - WET framework places header above and footer below */}
      <main id="wb-cont" property="mainContentOfPage" className="container">
        <div className="row">
          <div className="col-md-12">
            {children}
          </div>
        </div>
      </main>
    </>
  );
};

export default ClientLayout;
