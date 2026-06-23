// TypeScript mirror of the backend JSON contract (see backend/app/analytics).
// The frontend holds no fund math -- these are read-only shapes it renders.

export type WindowCode = "MTD" | "QTD" | "YTD" | "1Y" | "ALL";

export interface DataQuality {
  ok: boolean;
  count: number;
  issues: { source: string; reason: string; detail: string }[];
}

export interface Meta {
  has_data: boolean;
  windows: WindowCode[];
  default_window: WindowCode;
  as_of: string;
  inception: string;
  holdings_count: number;
  base_currency: string;
  sectors: string[];
  regions: string[];
  data_quality: DataQuality;
}

export interface Contribution {
  ticker: string;
  name: string;
  weight: number;
  return: number;
  contribution: number;
}

export interface Summary {
  window: WindowCode;
  as_of: string;
  base_currency: string;
  aum: number;
  pnl: { unrealised: number; realised: number; total: number };
  total_return: number;
  benchmark_return: number;
  active_return: number;
  holdings_count: number;
  top_contributors: Contribution[];
  top_detractors: Contribution[];
  truncated: boolean;
  data_quality: DataQuality;
}

export interface GroupWeight {
  sector?: string;
  region?: string;
  portfolio: number;
  benchmark: number;
  active: number;
}

export interface Exposure {
  window: WindowCode;
  as_of: string;
  sector: GroupWeight[];
  region: GroupWeight[];
  concentration: {
    hhi: number;
    effective_n: number;
    largest_weight: number;
    top5_weight: number;
  };
  heatmap: { sectors: string[]; regions: string[]; values: number[][] };
  data_quality: DataQuality;
}

export interface Risk {
  window: WindowCode;
  as_of: string;
  observations: number;
  volatility: number;
  annualised_return: number;
  beta: number | null;
  sharpe: number | null;
  max_drawdown: number;
  var: Record<string, { historical: number; parametric: number }>;
  risk_free_rate: number;
  correlation: { tickers: string[]; matrix: number[][] };
  truncated: boolean;
  data_quality: DataQuality;
}

export interface PeriodReturn {
  period: WindowCode;
  portfolio: number;
  benchmark: number;
  active: number;
  truncated: boolean;
}

export interface SecurityContribution {
  ticker: string;
  name: string;
  sector: string;
  weight: number;
  return: number;
  contribution: number;
}

export interface BrinsonRow {
  sector: string;
  w_portfolio: number;
  w_benchmark: number;
  r_portfolio: number;
  r_benchmark: number;
  allocation: number;
  selection: number;
  interaction: number;
  total: number;
}

export type Severity = "breach" | "warning";

export interface Alert {
  id: string;
  severity: Severity;
  category: string;
  title: string;
  detail: string;
  value: number;
  threshold: number;
}

export interface AlertFeed {
  window: WindowCode;
  as_of: string;
  counts: { breach: number; warning: number };
  alerts: Alert[];
  data_quality: DataQuality;
}

export interface ScenarioRequest {
  market: number;
  sector_shocks: Record<string, number>;
  fx_shocks: Record<string, number>;
}

export interface ScenarioHolding {
  ticker: string;
  name: string;
  sector: string;
  currency: string;
  beta: number;
  weight: number;
  shock_return: number;
  value_before: number;
  value_after: number;
  value_change: number;
}

export interface Scenario {
  as_of: string;
  inputs: ScenarioRequest;
  base_aum: number;
  new_aum: number;
  pnl_change: number;
  portfolio_return: number;
  top_gainers: ScenarioHolding[];
  top_losers: ScenarioHolding[];
  by_holding: ScenarioHolding[];
  data_quality: DataQuality;
}

export interface Attribution {
  window: WindowCode;
  as_of: string;
  period_returns: PeriodReturn[];
  security_contribution: SecurityContribution[];
  sector_contribution: { sector: string; contribution: number }[];
  brinson: BrinsonRow[];
  brinson_totals: {
    allocation: number;
    selection: number;
    interaction: number;
    total: number;
  };
  benchmark_return: number;
  truncated: boolean;
  data_quality: DataQuality;
}
