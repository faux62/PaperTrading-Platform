// Portfolio Optimizer Types

export type RiskProfile = 'prudent' | 'balanced' | 'aggressive';

export type OptimizationMethod = 
  | 'mean_variance'
  | 'min_variance'
  | 'max_sharpe'
  | 'risk_parity'
  | 'hrp'
  | 'black_litterman';

export type ProposalStatus = 'pending' | 'approved' | 'rejected' | 'executed' | 'expired';
export type ProposalType = 'initial' | 'rebalance' | 'tactical' | 'risk_reduction';

export interface Allocation {
  symbol: string;
  name: string;
  weight: number;
  shares?: number;
  value?: number;
  sector?: string;
  rationale: string;
  current_weight: number;
  change: number;
}

export interface PortfolioProposal {
  id: string;
  portfolio_id: string;
  proposal_type: ProposalType;
  status: ProposalStatus;
  created_at: string;
  expires_at?: string;
  
  allocations: Allocation[];
  cash_weight: number;
  
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
  max_drawdown: number;
  
  sector_weights: Record<string, number>;
  diversification_ratio: number;
  
  summary: string;
  methodology: string;
  considerations: string[];
  
  turnover: number;
  estimated_costs: number;
}

export interface OptimizationRequest {
  portfolio_id: string;
  method?: OptimizationMethod;
  universe?: string[];
  sectors?: string[];
  excluded_symbols?: string[];
  min_positions?: number;
  max_positions?: number;
  max_weight_per_asset?: number;
  min_weight_per_asset?: number;
}

export interface OptimizationResponse {
  success: boolean;
  proposal?: PortfolioProposal;
  screened_count: number;
  execution_time_ms: number;
  error?: string;
}

export interface OptimizationMethodInfo {
  id: OptimizationMethod;
  name: string;
  description: string;
  risk_profiles: RiskProfile[];
  requires_returns: boolean;
  requires_views?: boolean;
}

export interface ScreenerCriteria {
  type: string;
  metrics: string[];
  description: string;
}

export interface EfficientFrontierPoint {
  expected_return: number;
  expected_volatility: number;
  sharpe_ratio: number;
  weights: number[];
}
