import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  files?: Array<{
    name: string;
    size: number;
    type: string;
    url?: string;
  }>;
}

interface CopilotContextType {
  isOpen: boolean;
  messages: Message[];
  toggleCopilot: () => void;
  openCopilot: () => void;
  closeCopilot: () => void;
  sendMessage: (content: string, files?: File[]) => Promise<void>;
  clearMessages: () => void;
}

const CopilotContext = createContext<CopilotContextType | undefined>(undefined);

export const useCopilot = () => {
  const context = useContext(CopilotContext);
  if (!context) {
    throw new Error('useCopilot must be used within a CopilotProvider');
  }
  return context;
};

interface CopilotProviderProps {
  children: ReactNode;
}

export const CopilotProvider: React.FC<CopilotProviderProps> = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m FileBot Assistant. How can I help you today? You can upload files by dragging and dropping them here, or type your questions below.',
      timestamp: new Date(),
    },
  ]);

  const toggleCopilot = () => setIsOpen(!isOpen);
  const openCopilot = () => setIsOpen(true);
  const closeCopilot = () => setIsOpen(false);

  const sendMessage = async (content: string, files?: File[]) => {
    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
      files: files?.map(file => ({
        name: file.name,
        size: file.size,
        type: file.type,
      })),
    };

    setMessages(prev => [...prev, userMessage]);

    // 这里应该调用OpenClaw API来处理消息
    // 暂时模拟AI回复
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `I received your message: "${content}"${files ? ` and ${files.length} file(s)` : ''}. This is a demo response. In production, this would connect to OpenClaw backend.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    }, 1000);
  };

  const clearMessages = () => {
    setMessages([
      {
        id: '1',
        role: 'assistant',
        content: 'Hello! I\'m FileBot Assistant. How can I help you today? You can upload files by dragging and dropping them here, or type your questions below.',
        timestamp: new Date(),
      },
    ]);
  };

  // 确保默认状态为关闭（全屏模式）
  useEffect(() => {
    console.log('CopilotProvider mounted, isOpen:', isOpen);
    if (isOpen) {
      console.warn('isOpen was true on mount, forcing to false for full-screen default');
      setIsOpen(false);
    }
  }, []);

  return (
    <CopilotContext.Provider
      value={{
        isOpen,
        messages,
        toggleCopilot,
        openCopilot,
        closeCopilot,
        sendMessage,
        clearMessages,
      }}
    >
      {children}
    </CopilotContext.Provider>
  );
};