"""
Performance Metrics Calculator

Calculates comprehensive performance metrics for backtest results.
"""
import math
from typing import List
from datetime import datetime, timedelta

from shared.models.backtest import BacktestTrade, EquityPoint, PerformanceMetrics


class MetricsCalculator:
    """Calculates performance metrics from backtest results"""
    
    @staticmethod
    def calculate_metrics(
        trades: List[BacktestTrade],
        equity_curve: List[EquityPoint],
        initial_capital: float,
        start_date: datetime,
        end_date: datetime
    ) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            trades: List of completed trades
            equity_curve: Equity curve points
            initial_capital: Starting capital
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            PerformanceMetrics with all calculated metrics
        """
        if not trades:
            # No trades executed
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                average_win=0.0,
                average_loss=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                max_consecutive_wins=0,
                max_consecutive_losses=0,
                average_holding_time_seconds=0.0
            )
        
        # Calculate basic metrics
        total_return = MetricsCalculator._calculate_total_return(
            equity_curve, initial_capital
        )
        
        annualized_return = MetricsCalculator._calculate_annualized_return(
            total_return, start_date, end_date
        )
        
        max_drawdown = MetricsCalculator._calculate_max_drawdown(equity_curve)
        
        sharpe_ratio = MetricsCalculator._calculate_sharpe_ratio(
            equity_curve, initial_capital
        )
        
        sortino_ratio = MetricsCalculator._calculate_sortino_ratio(
            equity_curve, initial_capital
        )
        
        # Calculate trade statistics
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        win_rate = (len(winning_trades) / len(trades)) * 100 if trades else 0.0
        
        profit_factor = MetricsCalculator._calculate_profit_factor(
            winning_trades, losing_trades
        )
        
        average_win = (
            sum(t.pnl for t in winning_trades) / len(winning_trades)
            if winning_trades else 0.0
        )
        
        average_loss = (
            sum(t.pnl for t in losing_trades) / len(losing_trades)
            if losing_trades else 0.0
        )
        
        max_consecutive_wins = MetricsCalculator._calculate_max_consecutive_wins(trades)
        max_consecutive_losses = MetricsCalculator._calculate_max_consecutive_losses(trades)
        
        average_holding_time = (
            sum(t.holding_time_seconds for t in trades) / len(trades)
            if trades else 0.0
        )
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            average_win=average_win,
            average_loss=average_loss,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            average_holding_time_seconds=average_holding_time
        )
    
    @staticmethod
    def _calculate_total_return(equity_curve: List[EquityPoint], initial_capital: float) -> float:
        """Calculate total return percentage"""
        if not equity_curve or initial_capital == 0:
            return 0.0
        
        final_equity = equity_curve[-1].equity
        return ((final_equity - initial_capital) / initial_capital) * 100
    
    @staticmethod
    def _calculate_annualized_return(
        total_return: float,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate annualized return"""
        days = (end_date - start_date).days
        if days == 0:
            return 0.0
        
        years = days / 365.25
        if years == 0:
            return 0.0
        
        # Compound annual growth rate (CAGR)
        return_multiplier = 1 + (total_return / 100)
        annualized = (math.pow(return_multiplier, 1 / years) - 1) * 100
        
        return annualized
    
    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[EquityPoint]) -> float:
        """Calculate maximum drawdown percentage"""
        if not equity_curve:
            return 0.0
        
        max_dd = 0.0
        peak = equity_curve[0].equity
        
        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity
            
            drawdown = ((peak - point.equity) / peak) * 100 if peak > 0 else 0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    @staticmethod
    def _calculate_sharpe_ratio(equity_curve: List[EquityPoint], initial_capital: float) -> float:
        """
        Calculate Sharpe ratio (risk-adjusted return).
        
        Assumes risk-free rate of 0 for simplicity.
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate returns between equity points
        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i - 1].equity
            curr_equity = equity_curve[i].equity
            
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean and standard deviation of returns
        mean_return = sum(returns) / len(returns)
        
        if len(returns) < 2:
            return 0.0
        
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Sharpe ratio = mean return / std dev
        # Annualize by multiplying by sqrt(252) for daily returns
        sharpe = (mean_return / std_dev) * math.sqrt(252)
        
        return sharpe
    
    @staticmethod
    def _calculate_sortino_ratio(equity_curve: List[EquityPoint], initial_capital: float) -> float:
        """
        Calculate Sortino ratio (downside risk-adjusted return).
        
        Similar to Sharpe but only considers downside volatility.
        """
        if len(equity_curve) < 2:
            return 0.0
        
        # Calculate returns between equity points
        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i - 1].equity
            curr_equity = equity_curve[i].equity
            
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Calculate mean return
        mean_return = sum(returns) / len(returns)
        
        # Calculate downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            # No downside, return high Sortino ratio
            return 10.0
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_std = math.sqrt(downside_variance)
        
        if downside_std == 0:
            return 0.0
        
        # Sortino ratio = mean return / downside std dev
        # Annualize by multiplying by sqrt(252)
        sortino = (mean_return / downside_std) * math.sqrt(252)
        
        return sortino
    
    @staticmethod
    def _calculate_profit_factor(
        winning_trades: List[BacktestTrade],
        losing_trades: List[BacktestTrade]
    ) -> float:
        """
        Calculate profit factor (gross profit / gross loss).
        
        A profit factor > 1 means profitable strategy.
        """
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0.0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0.0
        
        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    @staticmethod
    def _calculate_max_consecutive_wins(trades: List[BacktestTrade]) -> int:
        """Calculate maximum consecutive winning trades"""
        if not trades:
            return 0
        
        max_wins = 0
        current_wins = 0
        
        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    @staticmethod
    def _calculate_max_consecutive_losses(trades: List[BacktestTrade]) -> int:
        """Calculate maximum consecutive losing trades"""
        if not trades:
            return 0
        
        max_losses = 0
        current_losses = 0
        
        for trade in trades:
            if trade.pnl < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    @staticmethod
    def get_trade_statistics(trades: List[BacktestTrade]) -> dict:
        """
        Get additional trade statistics.
        
        Returns:
            Dictionary with various trade statistics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'average_trade': 0.0,
                'median_trade': 0.0
            }
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl < 0]
        
        pnls = [t.pnl for t in trades]
        pnls_sorted = sorted(pnls)
        
        return {
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'largest_win': max(pnls) if pnls else 0.0,
            'largest_loss': min(pnls) if pnls else 0.0,
            'average_trade': sum(pnls) / len(pnls) if pnls else 0.0,
            'median_trade': pnls_sorted[len(pnls_sorted) // 2] if pnls_sorted else 0.0
        }
