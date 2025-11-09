"""
Performance Metrics Calculator

This module calculates comprehensive performance metrics including returns,
risk-adjusted metrics, drawdowns, and equity curves.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import numpy as np
from collections import defaultdict

from analytics_service.models import (
    AnalyticsPeriod, PerformanceMetrics, StrategyPerformance,
    RiskMetrics, PerformanceSummary, EquityPoint, DrawdownPeriod
)
from shared.models.trade import Trade, TradeData
from shared.models.position import Position, PositionData
from shared.models.order import TradingMode


class PerformanceCalculator:
    """Calculates performance metrics from trade and position data"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def calculate_performance_summary(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod,
        initial_capital: float = 1000000.0
    ) -> PerformanceSummary:
        """
        Calculate complete performance summary for an account
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode (paper or live)
            period: Time period for analysis
            initial_capital: Starting capital amount
            
        Returns:
            PerformanceSummary with all metrics
        """
        # Get all closed positions for the period
        positions = self._get_closed_positions(account_id, trading_mode, period)
        
        # Calculate overall metrics
        metrics = self._calculate_metrics(positions, initial_capital, period)
        
        # Calculate strategy-level breakdown
        strategy_breakdown = self._calculate_strategy_breakdown(positions)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(account_id, trading_mode, positions)
        
        return PerformanceSummary(
            account_id=account_id,
            trading_mode=trading_mode.value,
            period=period,
            metrics=metrics,
            strategy_breakdown=strategy_breakdown,
            risk_metrics=risk_metrics
        )
    
    def generate_equity_curve(
        self,
        account_id: str,
        trading_mode: TradingMode,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 1000000.0
    ) -> List[EquityPoint]:
        """
        Generate equity curve from trade history
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            start_date: Start date
            end_date: End date
            initial_capital: Starting capital
            
        Returns:
            List of EquityPoint objects
        """
        # Get all closed positions ordered by close time
        positions = self.db.query(Position).filter(
            and_(
                Position.account_id == account_id,
                Position.trading_mode == trading_mode,
                Position.closed_at.isnot(None),
                Position.closed_at >= start_date,
                Position.closed_at <= end_date
            )
        ).order_by(Position.closed_at).all()
        
        equity_curve = []
        current_equity = initial_capital
        peak_equity = initial_capital
        previous_equity = initial_capital
        
        # Add starting point
        equity_curve.append(EquityPoint(
            timestamp=start_date,
            equity=current_equity,
            drawdown=0.0,
            daily_return=0.0
        ))
        
        for position in positions:
            # Update equity with realized P&L
            current_equity += float(position.realized_pnl)
            
            # Update peak
            if current_equity > peak_equity:
                peak_equity = current_equity
            
            # Calculate drawdown
            drawdown = ((peak_equity - current_equity) / peak_equity) * 100 if peak_equity > 0 else 0.0
            
            # Calculate daily return
            daily_return = ((current_equity - previous_equity) / previous_equity) * 100 if previous_equity > 0 else 0.0
            
            equity_curve.append(EquityPoint(
                timestamp=position.closed_at,
                equity=current_equity,
                drawdown=drawdown,
                daily_return=daily_return
            ))
            
            previous_equity = current_equity
        
        return equity_curve
    
    def calculate_drawdown_analysis(
        self,
        equity_curve: List[EquityPoint]
    ) -> List[DrawdownPeriod]:
        """
        Analyze drawdown periods from equity curve
        
        Args:
            equity_curve: List of equity points
            
        Returns:
            List of DrawdownPeriod objects
        """
        if not equity_curve:
            return []
        
        drawdown_periods = []
        in_drawdown = False
        drawdown_start = None
        max_drawdown = 0.0
        peak_equity = equity_curve[0].equity
        
        for i, point in enumerate(equity_curve):
            # Update peak
            if point.equity > peak_equity:
                # If we were in drawdown and recovered, close the period
                if in_drawdown and drawdown_start:
                    duration = (point.timestamp - drawdown_start).days
                    recovery_days = (point.timestamp - drawdown_start).days
                    
                    drawdown_periods.append(DrawdownPeriod(
                        start_date=drawdown_start,
                        end_date=point.timestamp,
                        recovery_date=point.timestamp,
                        drawdown_percent=max_drawdown,
                        duration_days=duration,
                        recovery_days=recovery_days
                    ))
                    
                    in_drawdown = False
                    drawdown_start = None
                    max_drawdown = 0.0
                
                peak_equity = point.equity
            
            # Check if we're in drawdown
            if point.equity < peak_equity:
                if not in_drawdown:
                    # Start new drawdown period
                    in_drawdown = True
                    drawdown_start = point.timestamp
                
                # Update max drawdown for this period
                current_drawdown = ((peak_equity - point.equity) / peak_equity) * 100
                if current_drawdown > max_drawdown:
                    max_drawdown = current_drawdown
        
        # If still in drawdown at end, add unrecovered period
        if in_drawdown and drawdown_start:
            duration = (equity_curve[-1].timestamp - drawdown_start).days
            drawdown_periods.append(DrawdownPeriod(
                start_date=drawdown_start,
                end_date=equity_curve[-1].timestamp,
                recovery_date=None,
                drawdown_percent=max_drawdown,
                duration_days=duration,
                recovery_days=None
            ))
        
        return drawdown_periods
    
    def _get_closed_positions(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod
    ) -> List[Position]:
        """Get all closed positions for the period"""
        return self.db.query(Position).filter(
            and_(
                Position.account_id == account_id,
                Position.trading_mode == trading_mode,
                Position.closed_at.isnot(None),
                Position.closed_at >= period.start_date,
                Position.closed_at <= period.end_date
            )
        ).all()
    
    def _calculate_metrics(
        self,
        positions: List[Position],
        initial_capital: float,
        period: AnalyticsPeriod
    ) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        if not positions:
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
                total_pnl=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                largest_win=0.0,
                largest_loss=0.0,
                average_trade_duration=0.0,
                consecutive_wins=0,
                consecutive_losses=0
            )
        
        # Calculate basic metrics
        total_pnl = sum(float(p.realized_pnl) for p in positions)
        winning_positions = [p for p in positions if float(p.realized_pnl) > 0]
        losing_positions = [p for p in positions if float(p.realized_pnl) < 0]
        
        total_trades = len(positions)
        winning_trades = len(winning_positions)
        losing_trades = len(losing_positions)
        
        gross_profit = sum(float(p.realized_pnl) for p in winning_positions)
        gross_loss = abs(sum(float(p.realized_pnl) for p in losing_positions))
        
        # Calculate returns
        total_return = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        # Calculate annualized return
        days = (period.end_date - period.start_date).days
        years = days / 365.0 if days > 0 else 1.0
        annualized_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0.0
        
        # Calculate win rate
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        
        # Calculate profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Calculate average win/loss
        average_win = gross_profit / winning_trades if winning_trades > 0 else 0.0
        average_loss = gross_loss / losing_trades if losing_trades > 0 else 0.0
        
        # Find largest win/loss
        largest_win = max((float(p.realized_pnl) for p in winning_positions), default=0.0)
        largest_loss = min((float(p.realized_pnl) for p in losing_positions), default=0.0)
        
        # Calculate average holding time
        holding_times = []
        for p in positions:
            if p.opened_at and p.closed_at:
                duration = (p.closed_at - p.opened_at).total_seconds() / 3600  # hours
                holding_times.append(duration)
        average_trade_duration = np.mean(holding_times) if holding_times else 0.0
        
        # Calculate consecutive wins/losses
        consecutive_wins, consecutive_losses = self._calculate_consecutive_streaks(positions)
        
        # Calculate Sharpe ratio
        returns = [float(p.realized_pnl) / initial_capital for p in positions]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        
        # Calculate Sortino ratio
        sortino_ratio = self._calculate_sortino_ratio(returns)
        
        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown(positions, initial_capital)
        
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
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            average_trade_duration=average_trade_duration,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses
        )
    
    def _calculate_strategy_breakdown(
        self,
        positions: List[Position]
    ) -> List[StrategyPerformance]:
        """Calculate performance breakdown by strategy"""
        strategy_positions = defaultdict(list)
        
        for position in positions:
            if position.strategy_id:
                strategy_positions[str(position.strategy_id)].append(position)
        
        breakdown = []
        for strategy_id, strat_positions in strategy_positions.items():
            # Calculate metrics for this strategy
            total_pnl = sum(float(p.realized_pnl) for p in strat_positions)
            winning = [p for p in strat_positions if float(p.realized_pnl) > 0]
            losing = [p for p in strat_positions if float(p.realized_pnl) < 0]
            
            total_trades = len(strat_positions)
            win_rate = (len(winning) / total_trades) * 100 if total_trades > 0 else 0.0
            
            gross_profit = sum(float(p.realized_pnl) for p in winning)
            gross_loss = abs(sum(float(p.realized_pnl) for p in losing))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
            
            average_win = gross_profit / len(winning) if winning else 0.0
            average_loss = gross_loss / len(losing) if losing else 0.0
            
            # Calculate max drawdown for strategy
            max_drawdown = self._calculate_max_drawdown(strat_positions, 1000000.0)
            
            # Calculate Sharpe ratio
            returns = [float(p.realized_pnl) / 1000000.0 for p in strat_positions]
            sharpe_ratio = self._calculate_sharpe_ratio(returns)
            
            # Assume initial capital for return calculation
            total_return = (total_pnl / 1000000.0) * 100
            
            breakdown.append(StrategyPerformance(
                strategy_id=strategy_id,
                strategy_name=f"Strategy {strategy_id[:8]}",  # Shortened ID
                total_return=total_return,
                win_rate=win_rate,
                total_trades=total_trades,
                profit_factor=profit_factor,
                average_win=average_win,
                average_loss=average_loss,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                total_pnl=total_pnl
            ))
        
        return breakdown
    
    def _calculate_risk_metrics(
        self,
        account_id: str,
        trading_mode: TradingMode,
        positions: List[Position]
    ) -> RiskMetrics:
        """Calculate risk-related metrics"""
        # Get current open positions for exposure calculation
        open_positions = self.db.query(Position).filter(
            and_(
                Position.account_id == account_id,
                Position.trading_mode == trading_mode,
                Position.closed_at.is_(None)
            )
        ).all()
        
        # Calculate total exposure
        total_exposure = sum(
            float(p.quantity) * float(p.current_price)
            for p in open_positions
        )
        
        # Calculate position sizes
        position_sizes = [
            float(p.quantity) * float(p.entry_price)
            for p in positions
        ]
        
        max_position_size = max(position_sizes) if position_sizes else 0.0
        average_position_size = np.mean(position_sizes) if position_sizes else 0.0
        
        # Calculate concentration risk (largest position as % of total)
        concentration_risk = (max_position_size / total_exposure) * 100 if total_exposure > 0 else 0.0
        
        # Calculate VaR (95% confidence)
        returns = [float(p.realized_pnl) for p in positions]
        value_at_risk = np.percentile(returns, 5) if returns else 0.0
        
        # Placeholder values for beta and correlation (would need benchmark data)
        beta = 1.0
        correlation = 0.0
        
        # Margin utilization (placeholder - would need account balance data)
        margin_utilization = 0.0
        
        return RiskMetrics(
            total_exposure=total_exposure,
            margin_utilization=margin_utilization,
            value_at_risk=abs(value_at_risk),
            beta=beta,
            correlation=correlation,
            max_position_size=max_position_size,
            average_position_size=average_position_size,
            concentration_risk=concentration_risk
        )
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return sharpe * np.sqrt(252)  # Annualized
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.05) -> float:
        """Calculate Sortino ratio (uses downside deviation)"""
        if not returns or len(returns) < 2:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        
        # Calculate downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return 0.0
        
        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0.0
        
        sortino = np.mean(excess_returns) / downside_deviation
        return sortino * np.sqrt(252)  # Annualized
    
    def _calculate_max_drawdown(self, positions: List[Position], initial_capital: float) -> float:
        """Calculate maximum drawdown percentage"""
        if not positions:
            return 0.0
        
        # Sort positions by close time
        sorted_positions = sorted(positions, key=lambda p: p.closed_at)
        
        equity = initial_capital
        peak = initial_capital
        max_dd = 0.0
        
        for position in sorted_positions:
            equity += float(position.realized_pnl)
            
            if equity > peak:
                peak = equity
            
            drawdown = ((peak - equity) / peak) * 100 if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_consecutive_streaks(self, positions: List[Position]) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses"""
        if not positions:
            return 0, 0
        
        # Sort by close time
        sorted_positions = sorted(positions, key=lambda p: p.closed_at)
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for position in sorted_positions:
            pnl = float(position.realized_pnl)
            
            if pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
        
        return max_wins, max_losses
