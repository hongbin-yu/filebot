import api from './api';

export interface Group {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  created_at: string;
  updated_at?: string;
  member_count: number;
  institution_id?: string;
  institution_name?: string;
}

export interface GroupDetail extends Group {
  members: MemberInfo[];
}

export interface MemberInfo {
  user_id: string;
  username: string;
  email: string;
  role: string;
}

export interface GroupCreate {
  name: string;
  description?: string;
}

export interface GroupUpdate {
  name?: string;
  description?: string;
}

export interface AddMemberRequest {
  user_id: string;
  role: string;
}

const groupService = {
  async list(institutionId?: string): Promise<Group[]> {
    const params = institutionId ? { institution_id: institutionId } : {};
    const response = await api.get('/groups/', { params });
    return response.data;
  },

  async get(id: string): Promise<GroupDetail> {
    const response = await api.get(`/groups/${id}`);
    return response.data;
  },

  async create(data: GroupCreate): Promise<Group> {
    const response = await api.post('/groups/', data);
    return response.data;
  },

  async update(id: string, data: GroupUpdate): Promise<Group> {
    const response = await api.put(`/groups/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/groups/${id}`);
  },

  async getMembers(groupId: string): Promise<MemberInfo[]> {
    const response = await api.get(`/groups/${groupId}/members`);
    return response.data;
  },

  async addMember(groupId: string, data: AddMemberRequest): Promise<MemberInfo> {
    const response = await api.post(`/groups/${groupId}/members`, data);
    return response.data;
  },

  async removeMember(groupId: string, userId: string): Promise<void> {
    await api.delete(`/groups/${groupId}/members/${userId}`);
  },
};

export default groupService;
