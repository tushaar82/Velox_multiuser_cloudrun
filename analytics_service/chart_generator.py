"""
Chart Data Generator

This module generates data structures for various analytics charts including
equity curves, drawdown charts, distribution histograms, and heatmaps.
"""

from typing import List, Dict, Any
from collections import defaultdict
import numpy as np

from analytics_service.models import (
    ChartData, EquityPoint, DrawdownPeriod, StrategyPerformance,
    ProfitByTime, ProfitByDay, TradeDetail
)


class ChartGenerator:
    """Generates chart data for analytics visualizations"""
    
    def generate_equity_curve_chart(
        self,
        equity_curve: List[EquityPoint],
        title: str = "Portfolio Equity Curve"
    ) -> ChartData:
        """
        Generate equity curve chart data
        
        Args:
            equity_curve: List of equity points
            title: Chart title
            
        Returns:
            ChartData for line chart
        """
        data_points = []
        
        for point in equity_curve:
            data_points.append({
                'timestamp': point.timestamp.isoformat(),
                'equity': point.equity,
                'date': point.timestamp.strftime('%Y-%m-%d %H:%M')
            })
        
        return ChartData(
            chart_type='equity_curve',
            title=title,
            x_axis_label='Date',
            y_axis_label='Portfolio Value (₹)',
            data_points=data_points,
            metadata={
                'initial_equity': equity_curve[0].equity if equity_curve else 0,
                'final_equity': equity_curve[-1].equity if equity_curve else 0,
                'total_points': len(equity_curve)
            }
        )
    
    def generate_drawdown_chart(
        self,
        equity_curve: List[EquityPoint],
        title: str = "Portfolio Drawdown"
    ) -> ChartData:
        """
        Generate drawdown chart data
        
        Args:
            equity_curve: List of equity points
            title: Chart title
            
        Returns:
            ChartData for area chart
        """
        data_points = []
        
        for point in equity_curve:
            data_points.append({
                'timestamp': point.timestamp.isoformat(),
                'drawdown': -point.drawdown,  # Negative for visual representation
                'date': point.timestamp.strftime('%Y-%m-%d %H:%M')
            })
        
        max_drawdown = max((p.drawdown for p in equity_curve), default=0.0)
        
        return ChartData(
            chart_type='drawdown',
            title=title,
            x_axis_label='Date',
            y_axis_label='Drawdown (%)',
            data_points=data_points,
            metadata={
                'max_drawdown': max_drawdown,
                'total_points': len(equity_curve)
            }
        )
    
    def generate_win_loss_distribution(
        self,
        trades: List[TradeDetail],
        title: str = "Win/Loss Distribution"
    ) -> ChartData:
        """
        Generate win/loss distribution histogram
        
        Args:
            trades: List of trade details
            title: Chart title
            
        Returns:
            ChartData for histogram
        """
        if not trades:
            return ChartData(
                chart_type='distribution',
                title=title,
                x_axis_label='P&L (₹)',
                y_axis_label='Frequency',
                data_points=[],
                metadata={'total_trades': 0}
            )
        
        # Extract P&L values
        pnl_values = [trade.pnl for trade in trades]
        
        # Create histogram bins
        num_bins = min(20, len(trades))
        hist, bin_edges = np.histogram(pnl_values, bins=num_bins)
        
        data_points = []
        for i in range(len(hist)):
            bin_start = bin_edges[i]
            bin_end = bin_edges[i + 1]
            bin_center = (bin_start + bin_end) / 2
            
            data_points.append({
                'bin_center': bin_center,
                'bin_start': bin_start,
                'bin_end': bin_end,
                'frequency': int(hist[i]),
                'label': f'₹{bin_start:.0f} to ₹{bin_end:.0f}'
            })
        
        return ChartData(
            chart_type='distribution',
            title=title,
            x_axis_label='P&L (₹)',
            y_axis_label='Number of Trades',
            data_points=data_points,
            metadata={
                'total_trades': len(trades),
                'mean_pnl': np.mean(pnl_values),
                'median_pnl': np.median(pnl_values),
                'std_pnl': np.std(pnl_values)
            }
        )
    
    def generate_profit_by_time_heatmap(
        self,
        profit_by_time: List[ProfitByTime],
        profit_by_day: List[ProfitByDay],
        title: str = "Profit Heatmap by Time"
    ) -> ChartData:
        """
        Generate profit heatmap by hour and day
        
        Args:
            profit_by_time: Hourly profit data
            profit_by_day: Daily profit data
            title: Chart title
            
        Returns:
            ChartData for heatmap
        """
        # Create hourly data points
        hourly_data = []
        for hour_data in profit_by_time:
            hourly_data.append({
                'hour': hour_data.hour,
                'profit': hour_data.profit,
                'trade_count': hour_data.trade_count,
                'win_rate': hour_data.win_rate,
                'label': f'{hour_data.hour:02d}:00'
            })
        
        # Create daily data points
        daily_data = []
        for day_data in profit_by_day:
            daily_data.append({
                'day': day_data.day,
                'profit': day_data.profit,
                'trade_count': day_data.trade_count,
                'win_rate': day_data.win_rate
            })
        
        return ChartData(
            chart_type='heatmap',
            title=title,
            x_axis_label='Hour of Day / Day of Week',
            y_axis_label='Profit (₹)',
            data_points=[
                {'type': 'hourly', 'data': hourly_data},
                {'type': 'daily', 'data': daily_data}
            ],
            metadata={
                'total_hours': len(profit_by_time),
                'total_days': len(profit_by_day)
            }
        )
    
    def generate_strategy_comparison_chart(
        self,
        strategy_breakdown: List[StrategyPerformance],
        title: str = "Strategy Performance Comparison"
    ) -> ChartData:
        """
        Generate strategy comparison bar chart
        
        Args:
            strategy_breakdown: List of strategy performance metrics
            title: Chart title
            
        Returns:
            ChartData for bar chart
        """
        data_points = []
        
        for strategy in strategy_breakdown:
            data_points.append({
                'strategy_id': strategy.strategy_id,
                'strategy_name': strategy.strategy_name,
                'total_return': strategy.total_return,
                'win_rate': strategy.win_rate,
                'total_trades': strategy.total_trades,
                'profit_factor': strategy.profit_factor,
                'sharpe_ratio': strategy.sharpe_ratio,
                'total_pnl': strategy.total_pnl
            })
        
        # Sort by total return
        data_points.sort(key=lambda x: x['total_return'], reverse=True)
        
        return ChartData(
            chart_type='comparison',
            title=title,
            x_axis_label='Strategy',
            y_axis_label='Total Return (%)',
            data_points=data_points,
            metadata={
                'total_strategies': len(strategy_breakdown),
                'best_strategy': data_points[0]['strategy_name'] if data_points else None,
                'worst_strategy': data_points[-1]['strategy_name'] if data_points else None
            }
        )
    
    def generate_monthly_returns_chart(
        self,
        equity_curve: List[EquityPoint],
        title: str = "Monthly Returns"
    ) -> ChartData:
        """
        Generate monthly returns bar chart
        
        Args:
            equity_curve: List of equity points
            title: Chart title
            
        Returns:
            ChartData for bar chart
        """
        if not equity_curve:
            return ChartData(
                chart_type='monthly_returns',
                title=title,
                x_axis_label='Month',
                y_axis_label='Return (%)',
                data_points=[],
                metadata={'total_months': 0}
            )
        
        # Group by month
        monthly_data = defaultdict(lambda: {'start': None, 'end': None})
        
        for point in equity_curve:
            month_key = point.timestamp.strftime('%Y-%m')
            
            if monthly_data[month_key]['start'] is None:
                monthly_data[month_key]['start'] = point.equity
            monthly_data[month_key]['end'] = point.equity
        
        # Calculate monthly returns
        data_points = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            start_equity = data['start']
            end_equity = data['end']
            
            if start_equity and end_equity and start_equity > 0:
                monthly_return = ((end_equity - start_equity) / start_equity) * 100
            else:
                monthly_return = 0.0
            
            data_points.append({
                'month': month_key,
                'return': monthly_return,
                'start_equity': start_equity,
                'end_equity': end_equity,
                'label': month_key
            })
        
        return ChartData(
            chart_type='monthly_returns',
            title=title,
            x_axis_label='Month',
            y_axis_label='Return (%)',
            data_points=data_points,
            metadata={
                'total_months': len(data_points),
                'average_monthly_return': np.mean([p['return'] for p in data_points]) if data_points else 0.0
            }
        )
    
    def generate_cumulative_pnl_chart(
        self,
        trades: List[TradeDetail],
        title: str = "Cumulative P&L"
    ) -> ChartData:
        """
        Generate cumulative P&L chart
        
        Args:
            trades: List of trade details
            title: Chart title
            
        Returns:
            ChartData for line chart
        """
        if not trades:
            return ChartData(
                chart_type='cumulative_pnl',
                title=title,
                x_axis_label='Trade Number',
                y_axis_label='Cumulative P&L (₹)',
                data_points=[],
                metadata={'total_trades': 0}
            )
        
        # Sort trades by exit date
        sorted_trades = sorted(trades, key=lambda t: t.exit_date)
        
        cumulative_pnl = 0.0
        data_points = []
        
        for i, trade in enumerate(sorted_trades, 1):
            cumulative_pnl += trade.pnl
            
            data_points.append({
                'trade_number': i,
                'cumulative_pnl': cumulative_pnl,
                'trade_pnl': trade.pnl,
                'symbol': trade.symbol,
                'date': trade.exit_date.strftime('%Y-%m-%d %H:%M')
            })
        
        return ChartData(
            chart_type='cumulative_pnl',
            title=title,
            x_axis_label='Trade Number',
            y_axis_label='Cumulative P&L (₹)',
            data_points=data_points,
            metadata={
                'total_trades': len(trades),
                'final_pnl': cumulative_pnl
            }
        )
    
    def generate_risk_return_scatter(
        self,
        strategy_breakdown: List[StrategyPerformance],
        title: str = "Risk-Return Profile"
    ) -> ChartData:
        """
        Generate risk-return scatter plot
        
        Args:
            strategy_breakdown: List of strategy performance metrics
            title: Chart title
            
        Returns:
            ChartData for scatter plot
        """
        data_points = []
        
        for strategy in strategy_breakdown:
            # Use max drawdown as risk measure
            risk = strategy.max_drawdown
            return_val = strategy.total_return
            
            data_points.append({
                'strategy_id': strategy.strategy_id,
                'strategy_name': strategy.strategy_name,
                'risk': risk,
                'return': return_val,
                'sharpe_ratio': strategy.sharpe_ratio,
                'total_trades': strategy.total_trades
            })
        
        return ChartData(
            chart_type='scatter',
            title=title,
            x_axis_label='Risk (Max Drawdown %)',
            y_axis_label='Return (%)',
            data_points=data_points,
            metadata={
                'total_strategies': len(strategy_breakdown)
            }
        )
