import React, { useState, useEffect } from 'react';
import aiService, { WebsiteCrawlStatus } from '../../services/ai.service';

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
      window.showWetAlert('Please enter a task ID');
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
      window.showWetAlert(`Cannot get status for task ${manualTaskId}: ${err}`);
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
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Task Monitor</h1>
          <p className="mt-2 text-gray-600">Monitor website crawling and other background task progress and status</p>
        </div>

        {/* Add task section */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Add Task</h2>
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={manualTaskId}
                onChange={(e) => setManualTaskId(e.target.value)}
                placeholder="Enter task ID (e.g., crawl_abc123def456)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <button
              onClick={handleAddTask}
              className="px-6 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Add Task
            </button>
          </div>
          <p className="mt-3 text-sm text-gray-500">
            Tip: Task ID can be obtained from API response or logs after website crawling, usually in format "crawl_xxxxxxxxxxxx"
          </p>
        </div>

        {/* 任务列表区域 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-800">Task List</h2>
            <div className="flex gap-3">
              <button
                onClick={refreshAllTasks}
                disabled={loading}
                className="px-4 py-2 bg-gray-100 text-gray-700 font-medium rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>

          {/* 加载和错误状态 */}
          {loading && (
            <div className="p-8 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading task list...</p>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700">{error}</p>
              </div>
            </div>
          )}

          {/* 任务表格 */}
          {!loading && !error && (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Task ID / Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      URL / Depth
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Progress / Stats
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Time / Action
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {tasks.map((task) => {
                    const progress = calculateProgress(task);
                    const isRefreshing = refreshingTasks.has(task.task_id);
                    
                    return (
                      <tr key={task.task_id} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="flex items-center">
                            <div className="flex-shrink-0">
                              <span className="text-lg">{getStatusIcon(task.status)}</span>
                            </div>
                            <div className="ml-4">
                              <div className="text-sm font-medium text-gray-900">
                                {task.task_id}
                              </div>
                              <div className="mt-1">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                                  {task.status.toUpperCase()}
                                  {isRefreshing && (
                                    <span className="ml-1 inline-block animate-spin h-3 w-3 border-b-2 border-current rounded-full"></span>
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm">
                            <div className="font-medium text-gray-900 truncate max-w-xs">
                              {task.url}
                            </div>
                            <div className="text-gray-500">
                              Depth: {task.depth}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="space-y-2">
                            {/* 进度条 */}
                            <div>
                              <div className="flex justify-between text-xs text-gray-600 mb-1">
                                <span>Progress</span>
                                <span>{progress}%</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
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
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div className="text-gray-600">
                                Pages: <span className="font-medium">{task.pages_crawled} / {task.pages_processed}</span>
                              </div>
                              <div className="text-gray-600">
                                Images: <span className="font-medium">{task.images_crawled}</span>
                              </div>
                              {task.errors.length > 0 && (
                                <div className="col-span-2 text-red-600">
                                  Errors: <span className="font-medium">{task.errors.length}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="space-y-2">
                            <div className="text-sm text-gray-900">
                              Start: {formatTime(task.started_at)}
                            </div>
                            <div className="text-sm text-gray-500">
                              Updated: {formatTime(task.updated_at)}
                            </div>
                            <div className="pt-2">
                              <button
                                onClick={() => refreshTaskStatus(task.task_id)}
                                disabled={isRefreshing}
                                className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
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
                <div className="text-center py-12">
                  <div className="inline-block p-4 bg-gray-100 rounded-full">
                    <span className="text-3xl">📋</span>
                  </div>
                  <h3 className="mt-4 text-lg font-medium text-gray-900">No Tasks</h3>
                  <p className="mt-2 text-gray-600">No task records found.</p>
                  <p className="mt-1 text-sm text-gray-500">
                    Use the input box above to add a task ID, or execute a new website crawling task.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 页脚信息 */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
            <div className="text-sm text-gray-600">
              <p>Running tasks are automatically refreshed every 10 seconds.</p>
              <p className="mt-1">Status: ⏳ Waiting | 🌐 Crawling | ⚙️ Processing | ✅ Completed | ❌ Failed | 🚫 Cancelled</p>
            </div>
          </div>
        </div>

        {/* 使用说明 */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-2">How to Use Task Monitor</h3>
          <ul className="space-y-2 text-blue-700">
            <li className="flex items-start">
              <span className="inline-block mr-2">1.</span>
              <span>When you execute a website crawl, you will receive a unique task ID</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block mr-2">2.</span>
              <span>Enter the task ID in the input box above to track task progress</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block mr-2">3.</span>
              <span>The system automatically refreshes running task status</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block mr-2">4.</span>
              <span>Click "Refresh" button to manually update individual task</span>
            </li>
            <li className="flex items-start">
              <span className="inline-block mr-2">5.</span>
              <span>Completed tasks show green, failed tasks show red with error details</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default AdminTasks;