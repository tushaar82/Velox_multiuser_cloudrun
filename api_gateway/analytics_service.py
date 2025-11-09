"""
Analytics Service Layer for API Gateway

This module provides the service layer for analytics operations,
handling business logic and coordinating with the analytics service.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from flask import Response
import json

from analytics_service.analytics_service import AnalyticsService
from analytics_service.models import AnalyticsPeriod, PeriodType
from shared.models.order import TradingMode


class AnalyticsServiceLayer:
    """Service layer for analytics operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.analytics_service = AnalyticsService(db_session)
    
    def get_performance_metrics(
        self,
        account_id: str,
        trading_mode: str,
        period_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for specified period
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode ('paper' or 'live')
            period_type: Period type ('daily', 'weekly', 'monthly', 'yearly', 'all', 'custom')
            start_date: Start date for custom period (ISO format)
            end_date: End date for custom period (ISO format)
            
        Returns:
            Dictionary with performance metrics
        """
        # Parse period
        period = self._parse_period(period_type, start_date, end_date)
        
        # Get trading mode enum
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        
        # Get performance summary
        summary = self.analytics_service.get_performance_metrics(
            account_id=account_id,
            trading_mode=mode,
            period=period
        )
        
        return self._serialize_performance_summary(summary)
    
    def get_equity_curve(
        self,
        account_id: str,
        trading_mode: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get equity curve data
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            Dictionary with equity curve data
        """
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        equity_curve = self.analytics_service.get_equity_curve(
            account_id=account_id,
            trading_mode=mode,
            start_date=start,
            end_date=end
        )
        
        return {
            'equity_curve': [
                {
                    'timestamp': point.timestamp.isoformat(),
                    'equity': point.equity,
                    'drawdown': point.drawdown,
                    'daily_return': point.daily_return
                }
                for point in equity_curve
            ]
        }
    
    def get_strategy_breakdown(
        self,
        account_id: str,
        trading_mode: str,
        period_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get strategy-level performance breakdown
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period_type: Period type
            start_date: Start date for custom period
            end_date: End date for custom period
            
        Returns:
            Dictionary with strategy breakdown
        """
        period = self._parse_period(period_type, start_date, end_date)
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        
        summary = self.analytics_service.get_performance_metrics(
            account_id=account_id,
            trading_mode=mode,
            period=period
        )
        
        return {
            'strategies': [
                {
                    'strategy_id': strat.strategy_id,
                    'strategy_name': strat.strategy_name,
                    'total_return': strat.total_return,
                    'win_rate': strat.win_rate,
                    'total_trades': strat.total_trades,
                    'profit_factor': strat.profit_factor,
                    'average_win': strat.average_win,
                    'average_loss': strat.average_loss,
                    'max_drawdown': strat.max_drawdown,
                    'sharpe_ratio': strat.sharpe_ratio,
                    'total_pnl': strat.total_pnl
                }
                for strat in summary.strategy_breakdown
            ]
        }
    
    def get_trade_analysis(
        self,
        account_id: str,
        trading_mode: str,
        period_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get detailed trade analysis
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period_type: Period type
            start_date: Start date for custom period
            end_date: End date for custom period
            
        Returns:
            Dictionary with trade analysis
        """
        period = self._parse_period(period_type, start_date, end_date)
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        
        statistics = self.analytics_service.get_trade_analysis(
            account_id=account_id,
            trading_mode=mode,
            period=period
        )
        
        return {
            'average_holding_time': statistics.average_holding_time,
            'median_holding_time': statistics.median_holding_time,
            'best_trade': self._serialize_trade_detail(statistics.best_trade) if statistics.best_trade else None,
            'worst_trade': self._serialize_trade_detail(statistics.worst_trade) if statistics.worst_trade else None,
            'consecutive_wins': statistics.consecutive_wins,
            'consecutive_losses': statistics.consecutive_losses,
            'profit_by_time_of_day': [
                {
                    'hour': p.hour,
                    'profit': p.profit,
                    'trade_count': p.trade_count,
                    'win_rate': p.win_rate
                }
                for p in statistics.profit_by_time_of_day
            ],
            'profit_by_day_of_week': [
                {
                    'day': p.day,
                    'profit': p.profit,
                    'trade_count': p.trade_count,
                    'win_rate': p.win_rate
                }
                for p in statistics.profit_by_day_of_week
            ],
            'average_win_holding_time': statistics.average_win_holding_time,
            'average_loss_holding_time': statistics.average_loss_holding_time,
            'win_loss_ratio': statistics.win_loss_ratio
        }
    
    def compare_to_benchmark(
        self,
        account_id: str,
        trading_mode: str,
        benchmark_name: str,
        period_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare performance to benchmark
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            benchmark_name: Benchmark index name
            period_type: Period type
            start_date: Start date for custom period
            end_date: End date for custom period
            
        Returns:
            Dictionary with benchmark comparison
        """
        period = self._parse_period(period_type, start_date, end_date)
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        
        comparison = self.analytics_service.compare_to_benchmark(
            account_id=account_id,
            trading_mode=mode,
            period=period,
            benchmark_name=benchmark_name
        )
        
        return {
            'benchmark_name': comparison.benchmark_name,
            'portfolio_return': comparison.portfolio_return,
            'benchmark_return': comparison.benchmark_return,
            'alpha': comparison.alpha,
            'beta': comparison.beta,
            'correlation': comparison.correlation,
            'tracking_error': comparison.tracking_error,
            'information_ratio': comparison.information_ratio
        }
    
    def export_report(
        self,
        account_id: str,
        trading_mode: str,
        format: str,
        period_type: str,
        benchmark_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Response:
        """
        Export analytics report
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            format: Export format ('pdf' or 'csv')
            period_type: Period type
            benchmark_name: Benchmark for comparison (optional)
            start_date: Start date for custom period
            end_date: End date for custom period
            
        Returns:
            Flask Response with file download
        """
        period = self._parse_period(period_type, start_date, end_date)
        mode = TradingMode.PAPER if trading_mode == 'paper' else TradingMode.LIVE
        
        # Generate complete report
        report = self.analytics_service.generate_complete_report(
            account_id=account_id,
            trading_mode=mode,
            period=period,
            benchmark_name=benchmark_name
        )
        
        if format == 'csv':
            csv_data = self.analytics_service.export_report_csv(report)
            return Response(
                csv_data.getvalue(),
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename=analytics_report_{account_id}_{trading_mode}.csv'
                }
            )
        elif format == 'pdf':
            # PDF export would require additional library (e.g., reportlab)
            # For now, return JSON with message
            return Response(
                json.dumps({'error': 'PDF export not yet implemented'}),
                mimetype='application/json',
                status=501
            )
        else:
            return Response(
                json.dumps({'error': 'Invalid format. Use csv or pdf'}),
                mimetype='application/json',
                status=400
            )
    
    def _parse_period(
        self,
        period_type: str,
        start_date: Optional[str],
        end_date: Optional[str]
    ) -> AnalyticsPeriod:
        """Parse period parameters into AnalyticsPeriod"""
        now = datetime.now()
        
        if period_type == 'daily':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period_type == 'weekly':
            start = now - timedelta(days=7)
            end = now
        elif period_type == 'monthly':
            start = now - timedelta(days=30)
            end = now
        elif period_type == 'yearly':
            start = now - timedelta(days=365)
            end = now
        elif period_type == 'all':
            start = datetime(2020, 1, 1)  # Platform start date
            end = now
        elif period_type == 'custom':
            if not start_date or not end_date:
                raise ValueError("start_date and end_date required for custom period")
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        else:
            raise ValueError(f"Invalid period_type: {period_type}")
        
        return AnalyticsPeriod(
            period=period_type,
            start_date=start,
            end_date=end
        )
    
    def _serialize_performance_summary(self, summary) -> Dict[str, Any]:
        """Serialize PerformanceSummary to dictionary"""
        return {
            'account_id': summary.account_id,
            'trading_mode': summary.trading_mode,
            'period': {
                'type': summary.period.period,
                'start_date': summary.period.start_date.isoformat(),
                'end_date': summary.period.end_date.isoformat()
            },
            'metrics': {
                'total_return': summary.metrics.total_return,
                'annualized_return': summary.metrics.annualized_return,
                'max_drawdown': summary.metrics.max_drawdown,
                'sharpe_ratio': summary.metrics.sharpe_ratio,
                'sortino_ratio': summary.metrics.sortino_ratio,
                'win_rate': summary.metrics.win_rate,
                'profit_factor': summary.metrics.profit_factor,
                'average_win': summary.metrics.average_win,
                'average_loss': summary.metrics.average_loss,
                'total_trades': summary.metrics.total_trades,
                'winning_trades': summary.metrics.winning_trades,
                'losing_trades': summary.metrics.losing_trades,
                'total_pnl': summary.metrics.total_pnl,
                'gross_profit': summary.metrics.gross_profit,
                'gross_loss': summary.metrics.gross_loss,
                'largest_win': summary.metrics.largest_win,
                'largest_loss': summary.metrics.largest_loss,
                'average_trade_duration': summary.metrics.average_trade_duration,
                'consecutive_wins': summary.metrics.consecutive_wins,
                'consecutive_losses': summary.metrics.consecutive_losses
            },
            'risk_metrics': {
                'total_exposure': summary.risk_metrics.total_exposure,
                'margin_utilization': summary.risk_metrics.margin_utilization,
                'value_at_risk': summary.risk_metrics.value_at_risk,
                'beta': summary.risk_metrics.beta,
                'correlation': summary.risk_metrics.correlation,
                'max_position_size': summary.risk_metrics.max_position_size,
                'average_position_size': summary.risk_metrics.average_position_size,
                'concentration_risk': summary.risk_metrics.concentration_risk
            },
            'generated_at': summary.generated_at.isoformat()
        }
    
    def _serialize_trade_detail(self, trade) -> Dict[str, Any]:
        """Serialize TradeDetail to dictionary"""
        return {
            'trade_id': trade.trade_id,
            'symbol': trade.symbol,
            'side': trade.side,
            'entry_date': trade.entry_date.isoformat(),
            'exit_date': trade.exit_date.isoformat(),
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'quantity': trade.quantity,
            'pnl': trade.pnl,
            'pnl_percent': trade.pnl_percent,
            'commission': trade.commission,
            'holding_time': trade.holding_time,
            'strategy_id': trade.strategy_id,
            'strategy_name': trade.strategy_name
        }
