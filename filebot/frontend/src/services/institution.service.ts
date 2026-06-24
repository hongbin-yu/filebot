import api from './api';

export interface Institution {
  id: string;
  name: string;
  slug: string;
  description?: string;
  domain?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface InstitutionUpdate {
  name?: string;
  slug?: string;
  description?: string;
  domain?: string;
  is_active?: boolean;
}

class InstitutionService {
  async getInstitutions(): Promise<Institution[]> {
    const response = await api.get('/institutions/');
    return response.data;
  }

  async getAllInstitutions(): Promise<Institution[]> {
    const response = await api.get('/institutions/all');
    return response.data;
  }

  async getInstitution(id: string): Promise<Institution> {
    const response = await api.get(`/institutions/${id}`);
    return response.data;
  }

  async createInstitution(data: { name: string; slug: string; description?: string; domain?: string }): Promise<Institution> {
    const response = await api.post('/institutions/', data);
    return response.data;
  }

  async updateInstitution(id: string, data: InstitutionUpdate): Promise<Institution> {
    const response = await api.put(`/institutions/${id}`, data);
    return response.data;
  }

  async deleteInstitution(id: string): Promise<void> {
    await api.delete(`/institutions/${id}`);
  }
}

export default new InstitutionService();
