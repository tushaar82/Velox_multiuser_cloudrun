"""
Trade Analysis Service

This module provides detailed trade analysis including holding times,
best/worst trades, consecutive streaks, and profit patterns by time.
"""

from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_
from collections import defaultdict
import numpy as np

from analytics_service.models import (
    TradeStatistics, TradeDetail, ProfitByTime, ProfitByDay, AnalyticsPeriod
)
from shared.models.position import Position
from shared.models.order import TradingMode


class TradeAnalyzer:
    """Analyzes trade patterns and statistics"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def analyze_trades(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod
    ) -> TradeStatistics:
        """
        Perform comprehensive trade analysis
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode (paper or live)
            period: Time period for analysis
            
        Returns:
            TradeStatistics with detailed analysis
        """
        # Get all closed positions for the period
        positions = self._get_closed_positions(account_id, trading_mode, period)
        
        if not positions:
            return self._empty_statistics()
        
        # Calculate holding times
        holding_times = self._calculate_holding_times(positions)
        average_holding_time = np.mean(holding_times) if holding_times else 0.0
        median_holding_time = np.median(holding_times) if holding_times else 0.0
        
        # Find best and worst trades
        best_trade = self._find_best_trade(positions)
        worst_trade = self._find_worst_trade(positions)
        
        # Calculate consecutive streaks
        consecutive_wins, consecutive_losses = self._calculate_consecutive_streaks(positions)
        
        # Analyze profit by time of day
        profit_by_time = self._analyze_profit_by_time_of_day(positions)
        
        # Analyze profit by day of week
        profit_by_day = self._analyze_profit_by_day_of_week(positions)
        
        # Calculate win/loss holding times
        winning_positions = [p for p in positions if float(p.realized_pnl) > 0]
        losing_positions = [p for p in positions if float(p.realized_pnl) < 0]
        
        winning_times = self._calculate_holding_times(winning_positions)
        losing_times = self._calculate_holding_times(losing_positions)
        
        average_win_holding_time = np.mean(winning_times) if winning_times else 0.0
        average_loss_holding_time = np.mean(losing_times) if losing_times else 0.0
        
        # Calculate win/loss ratio
        average_win = np.mean([float(p.realized_pnl) for p in winning_positions]) if winning_positions else 0.0
        average_loss = abs(np.mean([float(p.realized_pnl) for p in losing_positions])) if losing_positions else 0.0
        win_loss_ratio = average_win / average_loss if average_loss > 0 else 0.0
        
        return TradeStatistics(
            average_holding_time=average_holding_time,
            median_holding_time=median_holding_time,
            best_trade=best_trade,
            worst_trade=worst_trade,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            profit_by_time_of_day=profit_by_time,
            profit_by_day_of_week=profit_by_day,
            average_win_holding_time=average_win_holding_time,
            average_loss_holding_time=average_loss_holding_time,
            win_loss_ratio=win_loss_ratio
        )
    
    def get_trade_details(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod
    ) -> List[TradeDetail]:
        """
        Get detailed information for all trades
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period: Time period
            
        Returns:
            List of TradeDetail objects
        """
        positions = self._get_closed_positions(account_id, trading_mode, period)
        
        trade_details = []
        for position in positions:
            if position.opened_at and position.closed_at:
                holding_time = (position.closed_at - position.opened_at).total_seconds() / 3600
                
                # Calculate P&L percentage
                entry_value = float(position.entry_price) * position.quantity
                pnl_percent = (float(position.realized_pnl) / entry_value) * 100 if entry_value > 0 else 0.0
                
                # Estimate commission (would need actual data from trades table)
                commission = entry_value * 0.0003  # 0.03% default
                
                trade_details.append(TradeDetail(
                    trade_id=str(position.id),
                    symbol=position.symbol,
                    side=position.side.value,
                    entry_date=position.opened_at,
                    exit_date=position.closed_at,
                    entry_price=float(position.entry_price),
                    exit_price=float(position.current_price),
                    quantity=position.quantity,
                    pnl=float(position.realized_pnl),
                    pnl_percent=pnl_percent,
                    commission=commission,
                    holding_time=holding_time,
                    strategy_id=str(position.strategy_id) if position.strategy_id else "manual",
                    strategy_name=f"Strategy {str(position.strategy_id)[:8]}" if position.strategy_id else "Manual"
                ))
        
        return trade_details
    
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
        ).order_by(Position.closed_at).all()
    
    def _calculate_holding_times(self, positions: List[Position]) -> List[float]:
        """Calculate holding times in hours for all positions"""
        holding_times = []
        for position in positions:
            if position.opened_at and position.closed_at:
                duration = (position.closed_at - position.opened_at).total_seconds() / 3600
                holding_times.append(duration)
        return holding_times
    
    def _find_best_trade(self, positions: List[Position]) -> Optional[TradeDetail]:
        """Find the most profitable trade"""
        if not positions:
            return None
        
        best_position = max(positions, key=lambda p: float(p.realized_pnl))
        
        if float(best_position.realized_pnl) <= 0:
            return None
        
        holding_time = (best_position.closed_at - best_position.opened_at).total_seconds() / 3600
        entry_value = float(best_position.entry_price) * best_position.quantity
        pnl_percent = (float(best_position.realized_pnl) / entry_value) * 100 if entry_value > 0 else 0.0
        commission = entry_value * 0.0003
        
        return TradeDetail(
            trade_id=str(best_position.id),
            symbol=best_position.symbol,
            side=best_position.side.value,
            entry_date=best_position.opened_at,
            exit_date=best_position.closed_at,
            entry_price=float(best_position.entry_price),
            exit_price=float(best_position.current_price),
            quantity=best_position.quantity,
            pnl=float(best_position.realized_pnl),
            pnl_percent=pnl_percent,
            commission=commission,
            holding_time=holding_time,
            strategy_id=str(best_position.strategy_id) if best_position.strategy_id else "manual",
            strategy_name=f"Strategy {str(best_position.strategy_id)[:8]}" if best_position.strategy_id else "Manual"
        )
    
    def _find_worst_trade(self, positions: List[Position]) -> Optional[TradeDetail]:
        """Find the worst losing trade"""
        if not positions:
            return None
        
        worst_position = min(positions, key=lambda p: float(p.realized_pnl))
        
        if float(worst_position.realized_pnl) >= 0:
            return None
        
        holding_time = (worst_position.closed_at - worst_position.opened_at).total_seconds() / 3600
        entry_value = float(worst_position.entry_price) * worst_position.quantity
        pnl_percent = (float(worst_position.realized_pnl) / entry_value) * 100 if entry_value > 0 else 0.0
        commission = entry_value * 0.0003
        
        return TradeDetail(
            trade_id=str(worst_position.id),
            symbol=worst_position.symbol,
            side=worst_position.side.value,
            entry_date=worst_position.opened_at,
            exit_date=worst_position.closed_at,
            entry_price=float(worst_position.entry_price),
            exit_price=float(worst_position.current_price),
            quantity=worst_position.quantity,
            pnl=float(worst_position.realized_pnl),
            pnl_percent=pnl_percent,
            commission=commission,
            holding_time=holding_time,
            strategy_id=str(worst_position.strategy_id) if worst_position.strategy_id else "manual",
            strategy_name=f"Strategy {str(worst_position.strategy_id)[:8]}" if worst_position.strategy_id else "Manual"
        )
    
    def _calculate_consecutive_streaks(self, positions: List[Position]) -> tuple:
        """Calculate maximum consecutive wins and losses"""
        if not positions:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for position in positions:
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
    
    def _analyze_profit_by_time_of_day(self, positions: List[Position]) -> List[ProfitByTime]:
        """Analyze profit distribution by hour of day"""
        hourly_data = defaultdict(lambda: {'profit': 0.0, 'trades': 0, 'wins': 0})
        
        for position in positions:
            if position.closed_at:
                hour = position.closed_at.hour
                pnl = float(position.realized_pnl)
                
                hourly_data[hour]['profit'] += pnl
                hourly_data[hour]['trades'] += 1
                if pnl > 0:
                    hourly_data[hour]['wins'] += 1
        
        profit_by_time = []
        for hour in range(24):
            data = hourly_data[hour]
            win_rate = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0.0
            
            profit_by_time.append(ProfitByTime(
                hour=hour,
                profit=data['profit'],
                trade_count=data['trades'],
                win_rate=win_rate
            ))
        
        return profit_by_time
    
    def _analyze_profit_by_day_of_week(self, positions: List[Position]) -> List[ProfitByDay]:
        """Analyze profit distribution by day of week"""
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        daily_data = defaultdict(lambda: {'profit': 0.0, 'trades': 0, 'wins': 0})
        
        for position in positions:
            if position.closed_at:
                day_index = position.closed_at.weekday()
                day_name = day_names[day_index]
                pnl = float(position.realized_pnl)
                
                daily_data[day_name]['profit'] += pnl
                daily_data[day_name]['trades'] += 1
                if pnl > 0:
                    daily_data[day_name]['wins'] += 1
        
        profit_by_day = []
        for day_name in day_names:
            data = daily_data[day_name]
            win_rate = (data['wins'] / data['trades']) * 100 if data['trades'] > 0 else 0.0
            
            profit_by_day.append(ProfitByDay(
                day=day_name,
                profit=data['profit'],
                trade_count=data['trades'],
                win_rate=win_rate
            ))
        
        return profit_by_day
    
    def _empty_statistics(self) -> TradeStatistics:
        """Return empty statistics when no trades exist"""
        return TradeStatistics(
            average_holding_time=0.0,
            median_holding_time=0.0,
            best_trade=None,
            worst_trade=None,
            consecutive_wins=0,
            consecutive_losses=0,
            profit_by_time_of_day=[
                ProfitByTime(hour=h, profit=0.0, trade_count=0, win_rate=0.0)
                for h in range(24)
            ],
            profit_by_day_of_week=[
                ProfitByDay(day=d, profit=0.0, trade_count=0, win_rate=0.0)
                for d in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            ],
            average_win_holding_time=0.0,
            average_loss_holding_time=0.0,
            win_loss_ratio=0.0
        )
