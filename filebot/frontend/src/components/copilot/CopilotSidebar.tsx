import React, { useState, useRef, DragEvent, useCallback } from 'react';
import { useCopilot } from '../../contexts/CopilotContext';

const CopilotSidebar: React.FC = () => {
  const { messages, sendMessage, closeCopilot } = useCopilot();
  const [inputValue, setInputValue] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() && selectedFiles.length === 0) {
      return;
    }

    await sendMessage(inputValue, selectedFiles);
    setInputValue('');
    setSelectedFiles([]);
  }, [inputValue, selectedFiles, sendMessage]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(2) + ' MB';
  };

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="w-full h-full bg-white flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-blue-50">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center mr-3">
            <span className="text-white font-bold">F</span>
          </div>
          <div>
            <h3 className="font-bold text-gray-800">FileBot Assistant</h3>
            <p className="text-xs text-gray-500">Powered by OpenClaw</p>
          </div>
        </div>
        <button
          onClick={closeCopilot}
          className="text-gray-500 hover:text-gray-700 p-2 rounded-full hover:bg-gray-100"
          aria-label="Close"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${message.role === 'user' 
                  ? 'bg-blue-100 text-blue-900 rounded-tr-none' 
                  : 'bg-gray-100 text-gray-900 rounded-tl-none'
                }`}
              >
                <div className="text-sm mb-1">
                  <span className="font-semibold">
                    {message.role === 'user' ? 'You' : 'FileBot Assistant'}
                  </span>
                  <span className="text-gray-500 ml-2 text-xs">
                    {formatTime(message.timestamp)}
                  </span>
                </div>
                <div className="whitespace-pre-wrap">{message.content}</div>
                
                {message.files && message.files.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-300 border-opacity-50">
                    <div className="text-xs font-medium text-gray-700 mb-1">Attached Files:</div>
                    <div className="space-y-1">
                      {message.files.map((file, index) => (
                        <div key={index} className="flex items-center text-xs text-gray-600 bg-white bg-opacity-50 p-2 rounded">
                          <svg className="w-4 h-4 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <div className="truncate flex-1">{file.name}</div>
                          <div className="text-gray-500 ml-2">{formatFileSize(file.size)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* File Drop Zone */}
      {selectedFiles.length === 0 && (
        <div
          className={`mx-4 mb-4 p-6 border-2 border-dashed rounded-xl text-center cursor-pointer transition-colors ${
            isDragging 
              ? 'border-blue-400 bg-blue-50' 
              : 'border-gray-300 hover:border-blue-300 hover:bg-blue-50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <svg className="w-12 h-12 mx-auto text-gray-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-sm text-gray-600 mb-1">
            {isDragging ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-xs text-gray-500">or click to browse</p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </div>
      )}

      {/* Selected Files Preview */}
      {selectedFiles.length > 0 && (
        <div className="mx-4 mb-4 p-4 bg-blue-50 rounded-xl">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-gray-700">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </div>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Clear all
            </button>
          </div>
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between bg-white p-2 rounded">
                <div className="flex items-center flex-1 min-w-0">
                  <svg className="w-4 h-4 text-gray-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div className="truncate text-sm">{file.name}</div>
                </div>
                <div className="flex items-center ml-2">
                  <div className="text-xs text-gray-500 mr-2">{formatFileSize(file.size)}</div>
                  <button
                    onClick={() => handleRemoveFile(index)}
                    className="text-gray-400 hover:text-red-500 p-1"
                    aria-label="Remove file"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={2}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() && selectedFiles.length === 0}
            className="self-end px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <div className="text-xs text-gray-500 mt-2 text-center">
          This assistant connects to OpenClaw backend for intelligent file management and automation.
        </div>
      </div>
    </div>
  );
};

export default CopilotSidebar;