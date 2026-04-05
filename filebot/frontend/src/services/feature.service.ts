import api from './api';

export interface FeatureStatus {
  feature: string;
  enabled: boolean;
  edition: string;
  description: string;
}

export interface EditionInfo {
  name: string;
  description: string;
  feature_count: number;
  features: Record<string, boolean>;
}

export interface AllFeaturesResponse {
  edition: string;
  features: Record<string, FeatureStatus>;
}

export interface EditionsResponse {
  editions: EditionInfo[];
  default: string;
}

class FeatureService {
  // 获取特定特性状态
  async getFeatureStatus(feature: string, edition?: string): Promise<FeatureStatus> {
    const params: Record<string, string> = { feature };
    if (edition) params.edition = edition;

    const response = await api.get('/features/status', { params });
    return response.data;
  }

  // 获取所有特性状态
  async getAllFeaturesStatus(edition?: string): Promise<AllFeaturesResponse> {
    const params: Record<string, string> = {};
    if (edition) params.edition = edition;

    const response = await api.get('/features/all', { params });
    return response.data;
  }

  // 设置产品版本
  async setEdition(edition: string): Promise<any> {
    const response = await api.post('/features/edition', { edition });
    return response.data;
  }

  // 获取当前产品版本
  async getCurrentEdition(): Promise<any> {
    const response = await api.get('/features/current-edition');
    return response.data;
  }

  // 获取所有可用版本
  async getAvailableEditions(): Promise<EditionsResponse> {
    const response = await api.get('/features/editions');
    return response.data;
  }

  // 快速检查特性是否可用
  async checkFeature(feature: string, edition?: string): Promise<any> {
    const params: Record<string, string> = { feature };
    if (edition) params.edition = edition;

    console.log('Calling /features/check with params:', params);
    const response = await api.get('/features/check', { params });
    console.log('Response from /features/check:', response.data);
    return response.data;
  }

  // 检查AI文档分类是否可用
  async isAIClassificationEnabled(): Promise<boolean> {
    try {
      console.log('Checking AI classification feature...');
      const response = await this.checkFeature('ai_document_classification');
      console.log('AI classification feature response:', response);
      return response.enabled;
    } catch (error) {
      console.warn('检查AI分类特性失败，默认禁用:', error);
      return false;
    }
  }

  // 检查AI语义搜索是否可用
  async isAISemanticSearchEnabled(): Promise<boolean> {
    try {
      const response = await this.checkFeature('ai_semantic_search');
      return response.enabled;
    } catch (error) {
      console.warn('检查AI语义搜索特性失败，默认禁用:', error);
      return false;
    }
  }

  // 检查AI文档摘要是否可用
  async isAIDocumentSummaryEnabled(): Promise<boolean> {
    try {
      const response = await this.checkFeature('ai_document_summary');
      return response.enabled;
    } catch (error) {
      console.warn('检查AI文档摘要特性失败，默认禁用:', error);
      return false;
    }
  }

  // 获取当前版本和特性状态
  async getCurrentEditionWithFeatures() {
    const [editionInfo, allFeatures] = await Promise.all([
      this.getCurrentEdition(),
      this.getAllFeaturesStatus()
    ]);

    return {
      ...editionInfo,
      allFeatures: allFeatures.features
    };
  }

  // 判断是否基础版
  async isBasicEdition(): Promise<boolean> {
    try {
      const editionInfo = await this.getCurrentEdition();
      return editionInfo.edition === 'basic';
    } catch (error) {
      console.warn('检查版本失败:', error);
      return false;
    }
  }

  // 判断是否专业版
  async isProfessionalEdition(): Promise<boolean> {
    try {
      const editionInfo = await this.getCurrentEdition();
      return editionInfo.edition === 'professional';
    } catch (error) {
      console.warn('检查版本失败:', error);
      return false;
    }
  }

  // 判断是否企业版
  async isEnterpriseEdition(): Promise<boolean> {
    try {
      const editionInfo = await this.getCurrentEdition();
      return editionInfo.edition === 'enterprise';
    } catch (error) {
      console.warn('检查版本失败:', error);
      return false;
    }
  }
}

export default new FeatureService();