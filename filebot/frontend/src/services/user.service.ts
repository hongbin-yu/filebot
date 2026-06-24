import api from './api';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  is_superuser: boolean;
  institution_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  password?: string;
  is_active?: boolean;
  institution_id?: string;
}

class UserService {
  async createUser(data: any): Promise<User> {
    const response = await api.post('/users/', data);
    return response.data;
  }

  async getUsers(): Promise<User[]> {
    const response = await api.get('/users/');
    return response.data;
  }

  async getUser(id: string): Promise<User> {
    const response = await api.get(`/users/${id}`);
    return response.data;
  }

  async updateUser(id: string, data: UserUpdate): Promise<User> {
    const response = await api.put(`/users/${id}`, data);
    return response.data;
  }

  async deleteUser(id: string): Promise<void> {
    await api.delete(`/users/${id}`);
  }

  async toggleActive(id: string): Promise<User> {
    const response = await api.put(`/users/${id}/toggle-active`);
    return response.data;
  }

  async getMe(): Promise<User> {
    const response = await api.get('/auth/me');
    return response.data;
  }

  async getUserGroups(userId: string): Promise<{id: string; name: string}[]> {
    const response = await api.get(`/users/${userId}/groups`);
    return response.data;
  }
}

export default new UserService();
