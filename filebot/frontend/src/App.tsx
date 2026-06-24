import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import Login from './pages/Login';
import Register from './pages/Register';
import ClientLogin from './pages/ClientLogin';
import CopilotSidebar from './components/copilot/CopilotSidebar';
import { CopilotProvider, useCopilot } from './contexts/CopilotContext';
import authService from './services/auth.service';
import ToastNotification from './components/common/ToastNotification';
import './App.css';

// 导入Admin组件
import AdminAppsDashboard from './pages/admin/AdminAppsDashboard';
import AdminAppFolders from './pages/admin/AdminAppFolders';
import AdminDocuments from './pages/admin/AdminDocuments';
import AdminUpload from './pages/admin/AdminUpload';
import AdminTasks from './pages/admin/AdminTasks';
import AdminGroups from './pages/admin/AdminGroups';
import AdminPermissions from './pages/admin/AdminPermissions';
import AdminUsers from './pages/admin/AdminUsers';
import AdminInstitutions from './pages/admin/AdminInstitutions';
import DocumentDetail from './pages/DocumentDetail';
import AdminPathView from './pages/admin/AdminPathView';
import PathDocumentView from './pages/PathDocumentView';

// 导入Client组件（暂时使用占位符）
import ClientAppSelection from './pages/ClientAppSelection';
import ClientDocuments from './pages/ClientDocuments';
import ClientDocumentDetail from './pages/ClientDocumentDetail';
import ClientNavigation from './pages/ClientNavigation';
import ClientAppFolders from './pages/ClientAppFolders';
import ClientLayout from './components/layout/ClientLayout';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = authService.isAuthenticated();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  
  return <>{children}</>;
};

// Client Protected Route Component
const ClientProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  // 开发模式：绕过认证以测试前端界面
  const DEV_MODE = true;
  
  if (!DEV_MODE) {
    const isAuthenticated = authService.isAuthenticated();
    
    if (!isAuthenticated) {
      return <Navigate to="/client/login" />;
    }
    
    // 检查用户是否有适当的角色（viewer, user, admin都可以访问Client）
    const userInfo = authService.getUserInfo();
    if (!userInfo) {
      console.warn('没有用户信息，但用户已认证');
    }
  } else {
    console.log('🔧 开发模式：绕过Client认证检查');
  }
  
  return <>{children}</>;
};

// Main App with Copilot integration
const MainAppContent: React.FC = () => {
  const { isOpen } = useCopilot();
  
  if (isOpen) {
    // 两栏布局模式：左边主系统，右边FileBot聊天窗口
    return (
      <div className="fb-d-flex" style={{minHeight:"100vh",background:"#f9fafb"}}>
        {/* 左边：主系统 (占主要空间) */}
        <div style={{flex:1,overflow:"auto"}}>
          <MainLayout />
        </div>
        
        {/* 右边：FileBot聊天窗口 (固定宽度) */}
        <div style={{width:384,borderLeft:"1px solid #e5e7eb"}}>
          <CopilotSidebar />
        </div>
      </div>
    );
  }
  
  // 全屏模式：简化系统界面
  return (
    <div style={{minHeight:"100vh"}}>
      <MainLayout />
    </div>
  );
};

function App() {
  return (
    <CopilotProvider>
      <ToastNotification />
      <Router basename="/">
        <Routes>
          {/* ==================== 公共路由 ==================== */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          
          {/* ==================== 路径式文档预览（Board文档） ==================== */}
          {/* URL示例: /boarding/canadasite/en/employment-social-development.html */}
          <Route path="/boarding/*" element={<PathDocumentView />} />
          
          {/* ==================== Client公共门户路由 ==================== */}
          {/* Client登录 */}
          <Route path="/client/login" element={
            <ClientLayout>
              <ClientLogin />
            </ClientLayout>
          } />
          
          {/* Client应用选择（公共门户入口） */}
          <Route path="/apps" element={
            <ClientProtectedRoute>
              <ClientLayout>
                <ClientAppSelection />
              </ClientLayout>
            </ClientProtectedRoute>
          } />
          
          {/* Client导航页面（侧边栏应用列表 + 缩略图网格） */}
          <Route path="/apps/:appSlug/navigation" element={
            <ClientProtectedRoute>
              <ClientLayout>
                <ClientNavigation />
              </ClientLayout>
            </ClientProtectedRoute>
          } />
          
          {/* Client文件夹文档列表 */}
          <Route path="/apps/:appSlug/folders/:folderId/documents" element={
            <ClientProtectedRoute>
              <ClientLayout>
                <ClientDocuments />
              </ClientLayout>
            </ClientProtectedRoute>
          } />
          
          {/* Client文档详情 */}
          <Route path="/documents/*" element={
            <ClientProtectedRoute>
              <ClientLayout>
                <ClientDocumentDetail />
              </ClientLayout>
            </ClientProtectedRoute>
          } />
          
          {/* Client文件夹浏览（通配路由放置末尾，避免干扰其他特定路由）
              捕获 /apps/:appSlug/... 中未匹配的路径作为文件夹路径 */}
          <Route path="/apps/:appSlug/*" element={
            <ClientProtectedRoute>
              <ClientLayout>
                <ClientAppFolders />
              </ClientLayout>
            </ClientProtectedRoute>
          } />
          
          {/* ==================== Admin管理后台路由 ==================== */}
          {/* Admin主布局（受保护路由） */}
          <Route path="/admin" element={
            <ProtectedRoute>
              <MainAppContent />
            </ProtectedRoute>
          }>
            {/* Admin首页重定向到应用列表 */}
            <Route index element={<Navigate to="/admin/apps" />} />
            
            {/* Admin应用列表 */}
            <Route path="apps" element={<AdminAppsDashboard />} />
            
            {/* Admin应用文件夹管理 */}
            <Route path="apps/:appSlug" element={<AdminAppFolders />} />
            
            {/* Admin文件夹文档列表 */}
            <Route path="apps/:appSlug/folders/:folderId/documents" element={<AdminDocuments />} />
            
            {/* Admin文档上传 - 新路由使用查询参数传递文件夹路径 */}
            <Route path="apps/:appSlug/upload" element={<AdminUpload />} />
            {/* Admin文档上传 - 旧路由保留兼容 */}
            <Route path="apps/:appSlug/folders/:folderId/upload" element={<AdminUpload />} />
            
            {/* Admin任务监控 */}
            <Route path="tasks" element={<AdminTasks />} />
            
            {/* Admin用户组管理 */}
            <Route path="groups" element={<AdminGroups />} />
            
            {/* Admin权限管理 */}
            <Route path="permissions" element={<AdminPermissions />} />

            {/* Admin用户管理 */}
            <Route path="users" element={<AdminUsers />} />

            {/* Admin机构管理 */}
            <Route path="institutions" element={<AdminInstitutions />} />
            
            {/* Admin路径视图（新URL模式：/admin/{app}/{path}） */}
            <Route path=":appSlug/*" element={<AdminPathView />} />
            
            {/* Admin文档详情 - 支持path和UUID */}
            <Route path="documents/*" element={<DocumentDetail />} />
            
            {/* 旧路由重定向 */}
            <Route path="*" element={<Navigate to="/admin/apps" />} />
          </Route>
          
          {/* ==================== 旧路由重定向（兼容性） ==================== */}
          {/* 根路径直接跳转到公共Apps页面 */}
          <Route path="/" element={<Navigate to="/apps" />} />
          
          {/* 旧Admin路由重定向 */}
          <Route path="/dashboard" element={<Navigate to="/admin/apps" />} />
          <Route path="/admin/dashboard" element={<Navigate to="/admin/apps" />} />
          
          {/* 旧Client路由重定向 */}
          <Route path="/client" element={<Navigate to="/apps" />} />
          <Route path="/client/apps" element={<Navigate to="/apps" />} />
          <Route path="/client/apps/:appId" element={<Navigate to="/apps/:appId" />} />
          <Route path="/client/apps/:appId/drawers/:drawerSlug/documents" element={<Navigate to="/apps/:appId" />} />
          
          {/* 404重定向到根路径 */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </Router>
    </CopilotProvider>
  );
}

export default App;