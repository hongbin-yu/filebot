import api from './api';

export interface Permission {
  id: string;
  user_id?: string;
  group_id?: string;
  institution_id?: string;
  institution_name?: string;
  resource_type: 'app' | 'folder';
  resource_id: string;
  permission_level: 'read' | 'write' | 'admin' | 'owner';
  expires_at?: string;
  created_at: string;
  updated_at?: string;
}

export interface PermissionCreate {
  user_id?: string;
  group_id?: string;
  resource_type: 'app' | 'folder';
  resource_id: string;
  permission_level: 'read' | 'write' | 'admin' | 'owner';
  expires_at?: string;
}

export interface PermissionCheckRequest {
  resource_type: 'app' | 'folder';
  resource_id: string;
  required_level: 'read' | 'write' | 'admin' | 'owner';
}

export interface PermissionCheckResponse {
  has_permission: boolean;
  actual_level?: string;
  message: string;
}

const permissionService = {
  async list(params?: {
    resource_type?: string;
    resource_id?: string;
    user_id?: string;
    group_id?: string;
  }): Promise<Permission[]> {
    const response = await api.get('/permissions/', { params });
    return response.data;
  },

  async create(data: PermissionCreate): Promise<Permission> {
    const response = await api.post('/permissions/', data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/permissions/${id}`);
  },

  async getUserPermissions(userId: string): Promise<Permission[]> {
    const response = await api.get(`/permissions/users/${userId}`);
    return response.data;
  },

  async check(data: PermissionCheckRequest): Promise<PermissionCheckResponse> {
    const response = await api.post('/permissions/check', data);
    return response.data;
  },
};

export default permissionService;
