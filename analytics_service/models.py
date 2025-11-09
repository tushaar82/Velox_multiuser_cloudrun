"""
Analytics Service Data Models

This module defines data classes for analytics calculations including
performance metrics, risk metrics, and trade statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class PeriodType(Enum):
    """Time period types for analytics"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ALL = "all"
    CUSTOM = "custom"


@dataclass
class AnalyticsPeriod:
    """Defines a time period for analytics calculations"""
    period: str  # 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom'
    start_date: datetime
    end_date: datetime
    
    def __post_init__(self):
        """Validate period dates"""
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before end_date")


@dataclass
class StrategyPerformance:
    """Performance metrics for a single strategy"""
    strategy_id: str
    strategy_name: str
    total_return: float  # Percentage return
    win_rate: float  # Percentage of winning trades
    total_trades: int
    profit_factor: float  # Gross profit / Gross loss
    average_win: float  # Average winning trade amount
    average_loss: float  # Average losing trade amount
    max_drawdown: float  # Maximum drawdown percentage
    sharpe_ratio: float  # Risk-adjusted return
    total_pnl: float  # Total profit/loss in rupees


@dataclass
class RiskMetrics:
    """Risk-related metrics for an account"""
    total_exposure: float  # Total capital at risk
    margin_utilization: float  # Percentage of margin used
    value_at_risk: float  # VaR at 95% confidence
    beta: float  # Beta relative to benchmark
    correlation: float  # Correlation with benchmark
    max_position_size: float  # Largest position size
    average_position_size: float  # Average position size
    concentration_risk: float  # Percentage in largest position


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    total_return: float  # Total return percentage
    annualized_return: float  # Annualized return percentage
    max_drawdown: float  # Maximum drawdown percentage
    sharpe_ratio: float  # Sharpe ratio
    sortino_ratio: float  # Sortino ratio (downside deviation)
    win_rate: float  # Percentage of winning trades
    profit_factor: float  # Gross profit / Gross loss
    average_win: float  # Average winning trade
    average_loss: float  # Average losing trade
    total_trades: int  # Total number of trades
    winning_trades: int  # Number of winning trades
    losing_trades: int  # Number of losing trades
    total_pnl: float  # Total profit/loss in rupees
    gross_profit: float  # Sum of all winning trades
    gross_loss: float  # Sum of all losing trades
    largest_win: float  # Largest winning trade
    largest_loss: float  # Largest losing trade
    average_trade_duration: float  # Average holding time in hours
    consecutive_wins: int  # Maximum consecutive winning trades
    consecutive_losses: int  # Maximum consecutive losing trades


@dataclass
class PerformanceSummary:
    """Complete performance summary for an account"""
    account_id: str
    trading_mode: str  # 'paper' or 'live'
    period: AnalyticsPeriod
    metrics: PerformanceMetrics
    strategy_breakdown: List[StrategyPerformance]
    risk_metrics: RiskMetrics
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProfitByTime:
    """Profit aggregated by hour of day"""
    hour: int  # 0-23
    profit: float  # Total profit for this hour
    trade_count: int  # Number of trades in this hour
    win_rate: float  # Win rate for this hour


@dataclass
class ProfitByDay:
    """Profit aggregated by day of week"""
    day: str  # 'Monday', 'Tuesday', etc.
    profit: float  # Total profit for this day
    trade_count: int  # Number of trades on this day
    win_rate: float  # Win rate for this day


@dataclass
class TradeDetail:
    """Detailed information about a single trade"""
    trade_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    commission: float
    holding_time: float  # Hours
    strategy_id: str
    strategy_name: str


@dataclass
class TradeStatistics:
    """Detailed trade analysis statistics"""
    average_holding_time: float  # Average holding time in hours
    median_holding_time: float  # Median holding time in hours
    best_trade: Optional[TradeDetail]  # Most profitable trade
    worst_trade: Optional[TradeDetail]  # Worst losing trade
    consecutive_wins: int  # Maximum consecutive wins
    consecutive_losses: int  # Maximum consecutive losses
    profit_by_time_of_day: List[ProfitByTime]  # Hourly profit distribution
    profit_by_day_of_week: List[ProfitByDay]  # Daily profit distribution
    average_win_holding_time: float  # Average holding time for wins
    average_loss_holding_time: float  # Average holding time for losses
    win_loss_ratio: float  # Average win / Average loss


@dataclass
class EquityPoint:
    """Single point in equity curve"""
    timestamp: datetime
    equity: float  # Portfolio value at this time
    drawdown: float  # Drawdown percentage at this time
    daily_return: float  # Daily return percentage


@dataclass
class DrawdownPeriod:
    """Information about a drawdown period"""
    start_date: datetime
    end_date: datetime
    recovery_date: Optional[datetime]  # None if not recovered
    drawdown_percent: float  # Maximum drawdown during period
    duration_days: int  # Duration of drawdown
    recovery_days: Optional[int]  # Days to recover (None if not recovered)


@dataclass
class BenchmarkComparison:
    """Comparison with benchmark index"""
    benchmark_name: str  # 'NIFTY 50', 'BANK NIFTY', etc.
    portfolio_return: float  # Portfolio return percentage
    benchmark_return: float  # Benchmark return percentage
    alpha: float  # Excess return over benchmark
    beta: float  # Portfolio beta relative to benchmark
    correlation: float  # Correlation with benchmark
    tracking_error: float  # Standard deviation of excess returns
    information_ratio: float  # Alpha / Tracking error


@dataclass
class ChartData:
    """Data for generating charts"""
    chart_type: str  # 'equity_curve', 'drawdown', 'distribution', 'heatmap', 'comparison'
    title: str
    x_axis_label: str
    y_axis_label: str
    data_points: List[Dict[str, Any]]  # Flexible structure for different chart types
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyticsReport:
    """Complete analytics report for export"""
    account_id: str
    trading_mode: str
    period: AnalyticsPeriod
    performance_summary: PerformanceSummary
    trade_statistics: TradeStatistics
    equity_curve: List[EquityPoint]
    drawdown_periods: List[DrawdownPeriod]
    benchmark_comparison: Optional[BenchmarkComparison]
    charts: List[ChartData]
    generated_at: datetime = field(default_factory=datetime.now)
