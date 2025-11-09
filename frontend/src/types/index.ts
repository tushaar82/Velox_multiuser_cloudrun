// User and Authentication Types
export enum UserRole {
  ADMIN = 'admin',
  TRADER = 'trader',
  INVESTOR = 'investor',
}

export interface User {
  id: string;
  email: string;
  role: UserRole;
  accountId: string;
  createdAt: string;
  isLocked: boolean;
}

export interface Session {
  token: string;
  userId: string;
  expiresAt: string;
  lastActivity: string;
}

export interface UserAccount {
  id: string;
  traderId: string;
  name: string;
  isActive: boolean;
  createdAt: string;
}

export interface InvestorInvitation {
  id: string;
  accountId: string;
  inviterId: string;
  inviteeEmail: string;
  status: 'pending' | 'accepted' | 'rejected' | 'expired';
  createdAt: string;
  expiresAt: string;
}

// Trading Mode
export type TradingMode = 'paper' | 'live';

// Broker Types
export interface BrokerConnection {
  id: string;
  accountId: string;
  brokerName: string;
  isConnected: boolean;
  lastConnectedAt?: string;
  createdAt: string;
}

export interface BrokerInfo {
  name: string;
  version: string;
  description: string;
  credentialsRequired: CredentialField[];
  supportedOrderTypes: string[];
  supportedExchanges: string[];
}

export interface CredentialField {
  name: string;
  type: string;
  description: string;
}

// Strategy Types
export interface Strategy {
  id: string;
  name: string;
  description: string;
  strategyType: 'pre_built';
  config: StrategyConfig;
  isPublic: boolean;
  createdBy: string;
  createdAt: string;
}

export interface StrategyConfig {
  parameters: StrategyParameter[];
  timeframes: string[];
  symbols: string[];
}

export interface StrategyParameter {
  name: string;
  type: 'integer' | 'float' | 'string' | 'boolean';
  default: any;
  min?: number;
  max?: number;
  description: string;
}

export interface ActiveStrategy {
  id: string;
  accountId: string;
  strategyId: string;
  tradingMode: TradingMode;
  status: 'running' | 'paused' | 'stopped' | 'error';
  config: any;
  startedAt: string;
  stoppedAt?: string;
}

// Order Types
export interface Order {
  id: string;
  accountId: string;
  strategyId: string;
  symbol: string;
  side: 'buy' | 'sell';
  quantity: number;
  orderType: 'market' | 'limit' | 'stop' | 'stop_limit';
  price?: number;
  stopPrice?: number;
  tradingMode: TradingMode;
  status: 'pending' | 'submitted' | 'partial' | 'filled' | 'cancelled' | 'rejected';
  filledQuantity: number;
  averagePrice: number;
  brokerOrderId?: string;
  createdAt: string;
  updatedAt: string;
}

// Position Types
export interface Position {
  id: string;
  accountId: string;
  strategyId: string;
  symbol: string;
  side: 'long' | 'short';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  realizedPnl: number;
  tradingMode: TradingMode;
  stopLoss?: number;
  takeProfit?: number;
  trailingStopLoss?: TrailingStopConfig;
  openedAt: string;
  closedAt?: string;
}

export interface TrailingStopConfig {
  enabled: boolean;
  percentage: number;
  currentStopPrice: number;
  highestPrice: number;
  lowestPrice: number;
}

// Risk Management Types
export interface RiskLimits {
  accountId: string;
  tradingMode: TradingMode;
  maxLossLimit: number;
  currentLoss: number;
  isBreached: boolean;
  breachedAt?: string;
  acknowledged: boolean;
}

export interface StrategyLimits {
  tradingMode: TradingMode;
  maxConcurrentStrategies: number;
  currentActiveCount: number;
  lastUpdated: string;
}

export interface RiskMetrics {
  totalExposure: number;
  marginUtilization: number;
  valueAtRisk: number;
  beta: number;
  correlation: number;
}

// Market Data Types
export interface Tick {
  symbol: string;
  price: number;
  volume: number;
  timestamp: string;
}

export interface Candle {
  symbol: string;
  timeframe: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
  isForming: boolean;
}

export interface IndicatorValue {
  symbol: string;
  timeframe: string;
  indicatorType: string;
  value: number | number[];
  timestamp: string;
}

// Backtest Types
export interface BacktestConfig {
  strategyId: string;
  symbols: string[];
  timeframes: string[];
  startDate: string;
  endDate: string;
  initialCapital: number;
  slippage: number;
  commission: number;
}

export interface BacktestResult {
  id: string;
  config: BacktestConfig;
  metrics: PerformanceMetrics;
  trades: BacktestTrade[];
  equityCurve: EquityPoint[];
  completedAt: string;
}

export interface BacktestTrade {
  entryDate: string;
  exitDate: string;
  symbol: string;
  side: 'long' | 'short';
  entryPrice: number;
  exitPrice: number;
  quantity: number;
  pnl: number;
  pnlPercent: number;
  commission: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  drawdown: number;
}

// Analytics Types
export interface PerformanceMetrics {
  totalReturn: number;
  annualizedReturn: number;
  maxDrawdown: number;
  sharpeRatio: number;
  sortinoRatio: number;
  winRate: number;
  profitFactor: number;
  averageWin: number;
  averageLoss: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
}

export interface StrategyPerformance {
  strategyId: string;
  strategyName: string;
  totalReturn: number;
  winRate: number;
  totalTrades: number;
  profitFactor: number;
}

export interface TradeStatistics {
  averageHoldingTime: number;
  bestTrade: BacktestTrade;
  worstTrade: BacktestTrade;
  consecutiveWins: number;
  consecutiveLosses: number;
  profitByTimeOfDay: ProfitByTime[];
  profitByDayOfWeek: ProfitByDay[];
}

export interface ProfitByTime {
  hour: number;
  profit: number;
}

export interface ProfitByDay {
  day: string;
  profit: number;
}

// Notification Types
export interface Notification {
  id: string;
  userId: string;
  type: string;
  title: string;
  message: string;
  severity: 'info' | 'warning' | 'error';
  readAt?: string;
  createdAt: string;
}

export interface NotificationPreferences {
  userId: string;
  preferences: {
    [key: string]: NotificationChannelConfig;
  };
}

export interface NotificationChannelConfig {
  enabled: boolean;
  channels: ('email' | 'sms' | 'in_app')[];
}

// Symbol Mapping Types
export interface SymbolMapping {
  standardSymbol: string;
  brokerName: string;
  brokerSymbol: string;
  brokerToken: string;
  exchange: string;
  instrumentType: string;
  lotSize: number;
  tickSize: number;
}

// Admin Types
export interface SystemHealth {
  activeUsers: number;
  totalOrders: number;
  cpuUsage: number;
  memoryUsage: number;
  databaseConnections: number;
  errorRate: number;
}

export interface AuditLog {
  timestamp: string;
  userId: string;
  action: string;
  resource: string;
  resourceId: string;
  ipAddress: string;
  result: 'success' | 'failure';
  details: any;
}

// Dashboard Types
export interface DashboardSummary {
  equity: number;
  dailyPnl: number;
  activeStrategies: number;
  openPositions: number;
  todayOrders: number;
}
