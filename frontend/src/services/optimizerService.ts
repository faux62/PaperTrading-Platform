// Portfolio Optimizer API Service

import api from './api';
import type {
  OptimizationRequest,
  OptimizationResponse,
  PortfolioProposal,
  OptimizationMethodInfo,
  ScreenerCriteria,
  EfficientFrontierPoint,
} from '../types/optimizer';

const BASE_URL = '/optimizer';

export const optimizerService = {
  /**
   * Request portfolio optimization
   */
  async optimize(request: OptimizationRequest): Promise<OptimizationResponse> {
    const response = await api.post<OptimizationResponse>(`${BASE_URL}/optimize`, request);
    return response.data;
  },

  /**
   * Get all proposals for current user
   */
  async getProposals(portfolioId?: string, status?: string): Promise<PortfolioProposal[]> {
    const params = new URLSearchParams();
    if (portfolioId) params.append('portfolio_id', portfolioId);
    if (status) params.append('status_filter', status);
    
    const response = await api.get<PortfolioProposal[]>(`${BASE_URL}/proposals?${params}`);
    return response.data;
  },

  /**
   * Get a specific proposal
   */
  async getProposal(proposalId: string): Promise<PortfolioProposal> {
    const response = await api.get<PortfolioProposal>(`${BASE_URL}/proposals/${proposalId}`);
    return response.data;
  },

  /**
   * Approve or reject a proposal
   */
  async actionProposal(
    proposalId: string, 
    action: 'approve' | 'reject',
    notes?: string
  ): Promise<PortfolioProposal> {
    const response = await api.post<PortfolioProposal>(
      `${BASE_URL}/proposals/${proposalId}/action`,
      { action, notes }
    );
    return response.data;
  },

  /**
   * Delete a proposal
   */
  async deleteProposal(proposalId: string): Promise<void> {
    await api.delete(`${BASE_URL}/proposals/${proposalId}`);
  },

  /**
   * Execute an approved proposal (create actual trades)
   */
  async executeProposal(proposalId: string): Promise<{
    success: boolean;
    proposal_id: string;
    trades_created: Array<{
      symbol: string;
      trade_type: string;
      quantity: number;
      price: number;
      estimated_value: number;
    }>;
    total_trades: number;
    message: string;
  }> {
    const response = await api.post(`${BASE_URL}/proposals/${proposalId}/execute`);
    return response.data;
  },

  /**
   * Check if rebalancing is needed
   */
  async checkRebalance(
    portfolioId: string, 
    threshold: number = 0.05
  ): Promise<OptimizationResponse> {
    const response = await api.post<OptimizationResponse>(`${BASE_URL}/rebalance-check`, {
      portfolio_id: portfolioId,
      threshold,
    });
    return response.data;
  },

  /**
   * Get efficient frontier data
   */
  async getEfficientFrontier(
    portfolioId: string,
    nPoints: number = 30,
    symbols?: string[]
  ): Promise<EfficientFrontierPoint[]> {
    const params = new URLSearchParams();
    params.append('n_points', nPoints.toString());
    if (symbols?.length) params.append('symbols', symbols.join(','));
    
    const response = await api.get<EfficientFrontierPoint[]>(
      `${BASE_URL}/efficient-frontier/${portfolioId}?${params}`
    );
    return response.data;
  },

  /**
   * Get available optimization methods
   */
  async getMethods(): Promise<OptimizationMethodInfo[]> {
    const response = await api.get<OptimizationMethodInfo[]>(`${BASE_URL}/methods`);
    return response.data;
  },

  /**
   * Get screener criteria
   */
  async getScreenerCriteria(): Promise<ScreenerCriteria[]> {
    const response = await api.get<ScreenerCriteria[]>(`${BASE_URL}/screener/criteria`);
    return response.data;
  },
};

export default optimizerService;
