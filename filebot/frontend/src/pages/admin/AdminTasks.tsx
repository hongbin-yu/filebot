import React, { useState, useEffect } from 'react';
import aiService, { WebsiteCrawlStatus } from '../../services/ai.service';
import { showToast } from '../../components/common/ToastNotification';

const AdminTasks: React.FC = () => {
  const [tasks, setTasks] = useState<WebsiteCrawlStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [manualTaskId, setManualTaskId] = useState('');
  const [refreshingTasks, setRefreshingTasks] = useState<Set<string>>(new Set());



  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        const result = await aiService.getCrawlTasks({ limit: 50 });
        setTasks(result.tasks);
      } catch (err) {
        console.error('Failed to load tasks:', err);
        setError('Unable to load task list.');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  // Auto-refresh running tasks
  useEffect(() => {
    const interval = setInterval(() => {
      const runningTasks = tasks.filter(task => 
        task.status === 'pending' || task.status === 'crawling' || task.status === 'processing'
      );
      
      runningTasks.forEach(task => {
        refreshTaskStatus(task.task_id);
      });
    }, 10000); // 每10秒刷新一次

    return () => clearInterval(interval);
  }, [tasks]);

  const refreshTaskStatus = async (taskId: string) => {
    try {
      setRefreshingTasks(prev => new Set(prev).add(taskId));
      const status = await aiService.getCrawlStatus(taskId);
      
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.task_id === taskId ? status : task
        )
      );
    } catch (err) {
      console.error(`Failed to refresh task status ${taskId}:`, err);
    } finally {
      setRefreshingTasks(prev => {
        const newSet = new Set(prev);
        newSet.delete(taskId);
        return newSet;
      });
    }
  };

  const handleAddTask = async () => {
    if (!manualTaskId.trim()) {
      showToast('Please enter a task ID', 'warning');
      return;
    }

    try {
      const status = await aiService.getCrawlStatus(manualTaskId);
      setTasks(prevTasks => {
        // 避免重复添加
        if (prevTasks.some(task => task.task_id === status.task_id)) {
          return prevTasks.map(task => 
            task.task_id === status.task_id ? status : task
          );
        }
        return [status, ...prevTasks];
      });
      setManualTaskId('');
    } catch (err) {
      console.error('Failed to get task status:', err);
      showToast(`Cannot get status for task ${manualTaskId}: ${err}`, 'error');
    }
  };

  const refreshAllTasks = async () => {
    try {
      setLoading(true);
      // 从API获取所有任务
      const result = await aiService.getCrawlTasks({ limit: 50 });
      setTasks(result.tasks);
      setError(null);
    } catch (err) {
      console.error('Failed to refresh task list:', err);
      setError('Refresh failed, please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'crawling': return 'bg-blue-100 text-blue-800';
      case 'processing': return 'bg-purple-100 text-purple-800';
      case 'completed': return 'bg-green-100 text-green-800';
      case 'failed': return 'bg-red-100 text-red-800';
      case 'cancelled': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'pending': return '⏳';
      case 'crawling': return '🌐';
      case 'processing': return '⚙️';
      case 'completed': return '✅';
      case 'failed': return '❌';
      case 'cancelled': return '🚫';
      default: return '❓';
    }
  };

  const formatTime = (timeString: string) => {
    const date = new Date(timeString);
    return date.toLocaleString('en-CA', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const calculateProgress = (task: WebsiteCrawlStatus) => {
    if (task.status === 'completed') return 100;
    if (task.status === 'failed' || task.status === 'cancelled') return 0;
    
    // 如果有页面统计，计算进度
    if (task.pages_crawled > 0 && task.pages_processed > 0) {
      return Math.min(100, Math.round((task.pages_processed / task.pages_crawled) * 100));
    }
    
    return 0;
  };

  return (
    <div style={{ minHeight:"100vh", background:"#f9fafb", padding:24 }}>
      <div className="container" style={{maxWidth:1280}}>
        {/* 页面标题 */}
        <div style={{marginBottom:32}}>
          <h1 style={{ fontSize:"1.875rem", fontWeight:700, color:"#111827" }}>Task Monitor</h1>
          <p  style={{ marginTop:8 }}>Monitor website crawling and other background task progress and status</p>
        </div>

        {/* Add task section */}
        <div style={{ background:"#ffffff", borderRadius:8, boxShadow:"0 1px 2px 0 rgba(0,0,0,0.05)", border:"1px solid #e5e7eb", borderColor:"#e5e7eb", padding:24, marginBottom:32 }}>
          <h2 style={{ fontSize:"1.25rem", fontWeight:600, color:"#1f2937", marginBottom:16 }}>Add Task</h2>
          <div style={{ display:"flex", gap:16 }}>
            <div style={{flex:1}}>
              <input
                type="text"
                value={manualTaskId}
                onChange={(e) => setManualTaskId(e.target.value)}
                placeholder="Enter task ID (e.g., crawl_abc123def456)"
                className="form-control" style={{borderRadius:8}}
              />
            </div>
            <button
              onClick={handleAddTask}
               style={{ paddingLeft:24, paddingTop:8, background:"#2563eb", color:"#ffffff", fontWeight:500, borderRadius:8 }}
            >
              Add Task
            </button>
          </div>
          <p  style={{ marginTop:12, fontSize:"0.875rem" }}>
            Tip: Task ID can be obtained from API response or logs after website crawling, usually in format "crawl_xxxxxxxxxxxx"
          </p>
        </div>

        {/* 任务列表区域 */}
        <div style={{ background:"#ffffff", borderRadius:8, boxShadow:"0 1px 2px 0 rgba(0,0,0,0.05)", border:"1px solid #e5e7eb", borderColor:"#e5e7eb", overflow:"hidden" }}>
          <div className="fb-justify-between fb-align-center" style={{ paddingLeft:24, paddingTop:16, borderBottom:"1px solid #e5e7eb", borderColor:"#e5e7eb", display:"flex" }}>
            <h2 style={{ fontSize:"1.25rem", fontWeight:600, color:"#1f2937" }}>Task List</h2>
            <div style={{ display:"flex", gap:12 }}>
              <button
                onClick={refreshAllTasks}
                disabled={loading}
                className="fb-label" style={{ paddingLeft:16, paddingTop:8, background:"#f3f4f6", color:"#374151", borderRadius:8 }}
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>

          {/* 加载和错误状态 */}
          {loading && (
            <div  style={{ padding:32 }}>
              <div className="fb-spinner" style={{height:32,width:32,borderWidth:2,borderColor:"#2563eb",borderRadius:"50%"}}></div>
              <p  style={{ marginTop:8 }}>Loading task list...</p>
            </div>
          )}

          {error && (
            <div style={{padding:24}}>
              <div style={{ background:"#fef2f2", border:"1px solid #e5e7eb", borderColor:"#fecaca", borderRadius:8, padding:16 }}>
                <p style={{color:"#b91c1c"}}>{error}</p>
              </div>
            </div>
          )}

          {/* 任务表格 */}
          {!loading && !error && (
            <div style={{overflowX:"auto"}}>
              <table className="fb-divide-y" style={{ minWidth:"100%", "--divide-color":"#e5e7eb" }}>
                <thead style={{background:"#f9fafb"}}>
                  <tr>
                    <th scope="col"  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                      Task ID / Status
                    </th>
                    <th scope="col"  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                      URL / Depth
                    </th>
                    <th scope="col"  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                      Progress / Stats
                    </th>
                    <th scope="col"  style={{ paddingLeft:24, paddingTop:12, fontSize:"0.75rem", fontWeight:500, textTransform:"uppercase", letterSpacing:"0.05em" }}>
                      Time / Action
                    </th>
                  </tr>
                </thead>
                <tbody className="table">
                  {tasks.map((task) => {
                    const progress = calculateProgress(task);
                    const isRefreshing = refreshingTasks.has(task.task_id);
                    
                    return (
                      <tr key={task.task_id} className="fb-hover-btn">
                        <td style={{ paddingLeft:24, paddingTop:16 }}>
                          <div className="fb-d-flex fb-align-center">
                            <div style={{flexShrink:0}}>
                              <span style={{fontSize:"1.125rem"}}>{getStatusIcon(task.status)}</span>
                            </div>
                            <div style={{marginLeft:16}}>
                              <div className="fb-label" style={{ fontSize:"0.875rem", color:"#111827" }}>
                                {task.task_id}
                              </div>
                              <div style={{marginTop:4}}>
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                                  {task.status.toUpperCase()}
                                  {isRefreshing && (
                                    <span className="fb-spinner" style={{  height:12,width:12 ,  marginLeft:4, display:"inline-block", borderBottomWidth:2, borderRadius:"50%"  }}></span>
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        </td>
                        <td style={{ paddingLeft:24, paddingTop:16 }}>
                          <div style={{fontSize:"0.875rem"}}>
                            <div className="fb-label" style={{ color:"#111827", overflow:"hidden", maxWidth:320 }}>
                              {task.url}
                            </div>
                            <div >
                              Depth: {task.depth}
                            </div>
                          </div>
                        </td>
                        <td style={{ paddingLeft:24, paddingTop:16 }}>
                          <div className="fb-space-y" style={{gap:8}}>
                            {/* 进度条 */}
                            <div>
                              <div className="fb-justify-between" style={{ display:"flex", fontSize:"0.75rem", marginBottom:4 }}>
                                <span>Progress</span>
                                <span>{progress}%</span>
                              </div>
                              <div  style={{ width:"100%", background:"#e5e7eb", borderRadius:"50%" }}>
                                <div 
                                  className={`h-2 rounded-full ${
                                    task.status === 'completed' ? 'bg-green-600' :
                                    task.status === 'failed' ? 'bg-red-600' :
                                    task.status === 'crawling' ? 'bg-blue-600' :
                                    'bg-yellow-600'
                                  }`}
                                  style={{ width: `${progress}%` }}
                                ></div>
                              </div>
                            </div>
                            
                            {/* 统计信息 */}
                            <div style={{ display:"grid", gridTemplateColumns:"repeat(2, minmax(0, 1fr))", gap:8, fontSize:"0.75rem" }}>
                              <div >
                                Pages: <span style={{fontWeight:500}}>{task.pages_crawled} / {task.pages_processed}</span>
                              </div>
                              <div >
                                Images: <span style={{fontWeight:500}}>{task.images_crawled}</span>
                              </div>
                              {task.errors.length > 0 && (
                                <div style={{ gridColumn:"span 2 / span 2", color:"#dc2626" }}>
                                  Errors: <span style={{fontWeight:500}}>{task.errors.length}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td style={{ paddingLeft:24, paddingTop:16 }}>
                          <div className="fb-space-y" style={{gap:8}}>
                            <div style={{ fontSize:"0.875rem", color:"#111827" }}>
                              Start: {formatTime(task.started_at)}
                            </div>
                            <div  style={{fontSize:"0.875rem"}}>
                              Updated: {formatTime(task.updated_at)}
                            </div>
                            <div style={{ paddingTop:8 }}>
                              <button
                                onClick={() => refreshTaskStatus(task.task_id)}
                                disabled={isRefreshing}
                                className="fb-align-center fb-label" style={{  paddingTop:6,paddingBottom:6 ,  display:"inline-flex", paddingLeft:12, border:"1px solid #e5e7eb", borderColor:"#d1d5db", fontSize:"0.75rem", borderRadius:8, color:"#374151", background:"#ffffff"  }}
                              >
                                {isRefreshing ? 'Refreshing...' : 'Refresh'}
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              
              {/* 空状态 */}
              {tasks.length === 0 && (
                <div  style={{paddingTop:48,paddingBottom:48}}>
                  <div style={{ display:"inline-block", padding:16, background:"#f3f4f6", borderRadius:"50%" }}>
                    <span style={{fontSize:"1.875rem"}}>📋</span>
                  </div>
                  <h3 className="fb-label" style={{ marginTop:16, fontSize:"1.125rem", color:"#111827" }}>No Tasks</h3>
                  <p  style={{ marginTop:8 }}>No task records found.</p>
                  <p  style={{ marginTop:4, fontSize:"0.875rem" }}>
                    Use the input box above to add a task ID, or execute a new website crawling task.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 页脚信息 */}
          <div style={{ paddingLeft:24, paddingTop:16, background:"#f9fafb", borderTop:"1px solid #e5e7eb", borderColor:"#e5e7eb" }}>
            <div  style={{fontSize:"0.875rem"}}>
              <p>Running tasks are automatically refreshed every 10 seconds.</p>
              <p style={{marginTop:4}}>Status: ⏳ Waiting | 🌐 Crawling | ⚙️ Processing | ✅ Completed | ❌ Failed | 🚫 Cancelled</p>
            </div>
          </div>
        </div>

        {/* 使用说明 */}
        <div style={{ marginTop:32, background:"#eff6ff", border:"1px solid #e5e7eb", borderColor:"#bfdbfe", borderRadius:8, padding:24 }}>
          <h3 style={{ fontSize:"1.125rem", fontWeight:600, color:"#1e40af", marginBottom:8 }}>How to Use Task Monitor</h3>
          <ul style={{ rowGap:8, color:"#1d4ed8" }}>
            <li className="fb-align-start" style={{ display:"flex" }}>
              <span style={{ display:"inline-block", marginRight:8 }}>1.</span>
              <span>When you execute a website crawl, you will receive a unique task ID</span>
            </li>
            <li className="fb-align-start" style={{ display:"flex" }}>
              <span style={{ display:"inline-block", marginRight:8 }}>2.</span>
              <span>Enter the task ID in the input box above to track task progress</span>
            </li>
            <li className="fb-align-start" style={{ display:"flex" }}>
              <span style={{ display:"inline-block", marginRight:8 }}>3.</span>
              <span>The system automatically refreshes running task status</span>
            </li>
            <li className="fb-align-start" style={{ display:"flex" }}>
              <span style={{ display:"inline-block", marginRight:8 }}>4.</span>
              <span>Click "Refresh" button to manually update individual task</span>
            </li>
            <li className="fb-align-start" style={{ display:"flex" }}>
              <span style={{ display:"inline-block", marginRight:8 }}>5.</span>
              <span>Completed tasks show green, failed tasks show red with error details</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default AdminTasks;