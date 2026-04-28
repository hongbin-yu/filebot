import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// 导入翻译资源
import enTranslations from './locales/en/common.json';
import zhTranslations from './locales/zh/common.json';
import frTranslations from './locales/fr/common.json';

// 配置i18next
i18n
  .use(LanguageDetector) // 检测用户语言
  .use(initReactI18next) // 将i18next传递给react-i18next
  .init({
    resources: {
      en: {
        translation: enTranslations
      },
      zh: {
        translation: zhTranslations
      },
      fr: {
        translation: frTranslations
      }
    },
    fallbackLng: 'en', // 默认语言为英语
    lng: 'en', // 显式设置当前语言为英语
    
    interpolation: {
      escapeValue: false // React已经对XSS进行了防护
    },
    
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng'
    },
    
    // 调试选项（开发环境）
    debug: import.meta.env.DEV,
    
    // 支持的语言
    supportedLngs: ['en', 'zh', 'fr']
  });

// 创建一个辅助函数用于编程式语言切换
export const changeLanguage = (lng: string) => {
  return i18n.changeLanguage(lng);
};

// 获取当前语言
export const getCurrentLanguage = () => {
  return i18n.language || 'en';
};

// 检查是否支持某种语言
export const isLanguageSupported = (lng: string) => {
  return ['en', 'zh', 'fr'].includes(lng);
};

export default i18n;