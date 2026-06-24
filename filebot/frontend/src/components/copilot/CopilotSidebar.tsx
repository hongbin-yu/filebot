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
    <div className="fb-d-flex" style={{width:"100%",height:"100%",backgroundColor:"#fff",flexDirection:"column"}}>
      {/* Header */}
      <div className="fb-d-flex fb-align-center fb-justify-between" style={{padding:16,borderBottom:"1px solid #e5e7eb",backgroundColor:"#eff6ff"}}>
        <div className="fb-d-flex fb-align-center">
          <div className="fb-d-flex fb-align-center" style={{width:32,height:32,backgroundColor:"#2563eb",borderRadius:9999,justifyContent:"center",marginRight:12}}>
            <span style={{color:"#fff",fontWeight:700}}>F</span>
          </div>
          <div>
            <h3 style={{fontWeight:700,color:"#1f2937"}}>FileBot Assistant</h3>
            <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem"}}>Powered by OpenClaw</p>
          </div>
        </div>
        <button
          onClick={closeCopilot}
          className="text-muted fb-link" style={{padding:8,borderRadius:9999}}
          aria-label="Close"
        >
          <svg style={{width:20,height:20}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages Area */}
      <div style={{flex:1,overflowY:"auto",padding:16}}>
        <div style={{display:"flex",flexDirection:"column",gap:16}}>
          {messages.map((message) => (
            <div
              key={message.id}
              className="fb-d-flex" style={{justifyContent:message.role === 'user' ? 'flex-end' : 'flex-start'}}
            >
              <div
              style={{maxWidth:"80%",borderRadius:16,padding:16,...(message.role === 'user' ? {backgroundColor:'#dbeafe',color:'#1e3a5f',borderTopRightRadius:0} : {backgroundColor:'#f3f4f6',color:'#111827',borderTopLeftRadius:0})}}
              >
                <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginBottom:4}}>
                  <span style={{fontWeight:600}}>
                    {message.role === 'user' ? 'You' : 'FileBot Assistant'}
                  </span>
                  <span className="text-muted" style={{marginLeft:8,fontSize:"0.75rem",lineHeight:"1rem"}}>
                    {formatTime(message.timestamp)}
                  </span>
                </div>
                <div style={{whiteSpace:"pre-wrap"}}>{message.content}</div>
                
                {message.files && message.files.length > 0 && (
                  <div style={{marginTop:12,paddingTop:12,borderTop:"1px solid #e5e7eb",borderColor:"rgba(209,213,219,0.5)"}}>
                    <div style={{fontSize:"0.75rem",lineHeight:"1rem",fontWeight:500,color:"#374151",marginBottom:4}}>Attached Files:</div>
                    <div style={{display:"flex",flexDirection:"column",gap:4}}>
                      {message.files.map((file, index) => (
                        <div key={index} className="fb-d-flex fb-align-center text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",backgroundColor:"#fff",padding:8,borderRadius:4}}>
                          <svg style={{width:16,height:16,marginRight:8,flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                          <div style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",flex:1}}>{file.name}</div>
                          <div className="text-muted" style={{marginLeft:8}}>{formatFileSize(file.size)}</div>
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
          className="text-center" style={{...(!isDragging && {borderColor:'#d1d5db'}),marginLeft:16,marginRight:16,marginBottom:16,padding:24,borderWidth:2,borderStyle:"dashed",borderRadius:12,cursor:"pointer",transitionProperty:"colors",...(isDragging ? {borderColor:'#60a5fa',backgroundColor:'#eff6ff'} : {})}}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <svg style={{width:48,height:48,marginLeft:"auto",marginRight:"auto",color:"#9ca3af",marginBottom:12}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-muted" style={{fontSize:"0.875rem",lineHeight:"1.25rem",marginBottom:4}}>
            {isDragging ? 'Drop files here' : 'Drag & drop files here'}
          </p>
          <p className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem"}}>or click to browse</p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{display:"none"}}
            onChange={handleFileSelect}
          />
        </div>
      )}

      {/* Selected Files Preview */}
      {selectedFiles.length > 0 && (
        <div style={{marginLeft:16,marginRight:16,marginBottom:16,padding:16,backgroundColor:"#eff6ff",borderRadius:12}}>
          <div className="fb-d-flex fb-align-center fb-justify-between" style={{marginBottom:8}}>
            <div style={{fontSize:"0.875rem",lineHeight:"1.25rem",fontWeight:500,color:"#374151"}}>
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </div>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-muted fb-link" style={{fontSize:"0.75rem",lineHeight:"1rem"}}
            >
              Clear all
            </button>
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:8,maxHeight:128,overflowY:"auto"}}>
            {selectedFiles.map((file, index) => (
              <div key={index} className="fb-d-flex fb-align-center fb-justify-between" style={{backgroundColor:"#fff",padding:8,borderRadius:4}}>
                <div className="fb-d-flex fb-align-center" style={{flex:1,minWidth:0}}>
                  <svg className="text-muted" style={{width:16,height:16,marginRight:8,flexShrink:0}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",fontSize:"0.875rem",lineHeight:"1.25rem"}}>{file.name}</div>
                </div>
                <div className="fb-d-flex fb-align-center" style={{marginLeft:8}}>
                  <div className="text-muted" style={{fontSize:"0.75rem",lineHeight:"1rem",marginRight:8}}>{formatFileSize(file.size)}</div>
                  <button
                    onClick={() => handleRemoveFile(index)}
                    style={{color:"#9ca3af",padding:4}}
                    aria-label="Remove file"
                  >
                    <svg style={{width:16,height:16}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      <div style={{borderTop:"1px solid #e5e7eb",padding:16}}>
        <div className="fb-d-flex" style={{display:"flex",gap:8}}>
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
            className="form-control" style={{flex:1,resize:"none",borderRadius:8}}
            rows={2}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() && selectedFiles.length === 0}
            style={{alignSelf:"flex-end",paddingLeft:24,paddingRight:24,paddingTop:12,paddingBottom:12,backgroundColor:"#2563eb",color:"#fff",borderRadius:8}}
          >
            <svg style={{width:20,height:20}} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <div className="text-muted text-center" style={{fontSize:"0.75rem",lineHeight:"1rem",marginTop:8}}>
          This assistant connects to OpenClaw backend for intelligent file management and automation.
        </div>
      </div>
    </div>
  );
};

export default CopilotSidebar;