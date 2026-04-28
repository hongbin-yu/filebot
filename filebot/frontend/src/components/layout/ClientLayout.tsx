import React, { useEffect, ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

interface ClientLayoutProps {
  children: ReactNode;
}

/**
 * ClientLayout - 客户端布局组件
 * 
 * 用于客户端路由 (/apps/*)，应用Canada.ca主题(WET框架)
 * 动态加载GCWeb主题CSS和WET-BOEW JS
 */
const ClientLayout: React.FC<ClientLayoutProps> = ({ children }) => {
  const location = useLocation();

  useEffect(() => {
    // 修改<html>标签属性以匹配WET框架要求
    const htmlElement = document.documentElement;
    htmlElement.classList.add('no-js');
    htmlElement.setAttribute('lang', 'en');
    htmlElement.setAttribute('dir', 'ltr');

    // 加载Canada.ca主题的CSS
    const loadThemeStyles = () => {
      // 检查是否已加载GCWeb主题CSS
      if (!document.querySelector('link[href*="theme.min.css"]')) {
        const themeLink = document.createElement('link');
        themeLink.rel = 'stylesheet';
        themeLink.href = '/gcweb/GCWeb/css/theme.min.css';
        themeLink.media = 'screen';
        document.head.appendChild(themeLink);
      }

      // 检查是否已加载WET-BOEW CSS
      if (!document.querySelector('link[href*="wet-boew.min.css"]')) {
        const wetLink = document.createElement('link');
        wetLink.rel = 'stylesheet';
        wetLink.href = '/gcweb/wet-boew/css/wet-boew.min.css';
        wetLink.media = 'screen';
        document.head.appendChild(wetLink);
      }

      // 检查是否已加载WET-BOEW JS
      if (!document.querySelector('script[src*="wet-boew.min.js"]')) {
        const wetScript = document.createElement('script');
        wetScript.src = '/gcweb/wet-boew/js/wet-boew.min.js';
        wetScript.async = true;
        document.body.appendChild(wetScript);
      }

      // 可选：加载GCWeb主题JS
      if (!document.querySelector('script[src*="theme.min.js"]')) {
        const themeScript = document.createElement('script');
        themeScript.src = '/gcweb/GCWeb/js/theme.min.js';
        themeScript.async = true;
        document.body.appendChild(themeScript);
      }
    };

    loadThemeStyles();

    // 清理函数（当离开客户端路由时）
    return () => {
      // 移除WET框架特定的<html>属性
      htmlElement.classList.remove('no-js');
      // 注意：不重置lang和dir，因为它们可能被其他页面使用
    };
  }, [location.pathname]);

  return (
    <>
      {/* WET框架需要特定的容器结构 */}
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