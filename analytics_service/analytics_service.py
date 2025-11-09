"""
Analytics Service

Main service that coordinates performance calculations, trade analysis,
benchmark comparisons, and chart generation.
"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from io import BytesIO
import csv

from analytics_service.models import (
    AnalyticsPeriod, PerformanceSummary, TradeStatistics,
    EquityPoint, BenchmarkComparison, ChartData, AnalyticsReport
)
from analytics_service.performance_calculator import PerformanceCalculator
from analytics_service.trade_analyzer import TradeAnalyzer
from analytics_service.benchmark_comparator import BenchmarkComparator
from analytics_service.chart_generator import ChartGenerator
from shared.models.order import TradingMode


class AnalyticsService:
    """Main analytics service coordinating all analytics operations"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.performance_calculator = PerformanceCalculator(db_session)
        self.trade_analyzer = TradeAnalyzer(db_session)
        self.benchmark_comparator = BenchmarkComparator(db_session)
        self.chart_generator = ChartGenerator()
    
    def get_performance_metrics(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod,
        initial_capital: float = 1000000.0
    ) -> PerformanceSummary:
        """
        Get comprehensive performance metrics for an account
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode (paper or live)
            period: Time period for analysis
            initial_capital: Starting capital amount
            
        Returns:
            PerformanceSummary with all metrics
        """
        return self.performance_calculator.calculate_performance_summary(
            account_id=account_id,
            trading_mode=trading_mode,
            period=period,
            initial_capital=initial_capital
        )
    
    def get_equity_curve(
        self,
        account_id: str,
        trading_mode: TradingMode,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 1000000.0
    ) -> List[EquityPoint]:
        """
        Get equity curve data for charting
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            start_date: Start date
            end_date: End date
            initial_capital: Starting capital
            
        Returns:
            List of EquityPoint objects
        """
        return self.performance_calculator.generate_equity_curve(
            account_id=account_id,
            trading_mode=trading_mode,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
    
    def get_trade_analysis(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod
    ) -> TradeStatistics:
        """
        Get detailed trade analysis
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period: Time period
            
        Returns:
            TradeStatistics with detailed analysis
        """
        return self.trade_analyzer.analyze_trades(
            account_id=account_id,
            trading_mode=trading_mode,
            period=period
        )
    
    def compare_to_benchmark(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod,
        benchmark_name: str = "NIFTY 50",
        initial_capital: float = 1000000.0
    ) -> BenchmarkComparison:
        """
        Compare portfolio performance to benchmark
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period: Time period
            benchmark_name: Name of benchmark index
            initial_capital: Starting capital
            
        Returns:
            BenchmarkComparison with relative metrics
        """
        # Get equity curve
        equity_curve = self.performance_calculator.generate_equity_curve(
            account_id=account_id,
            trading_mode=trading_mode,
            start_date=period.start_date,
            end_date=period.end_date,
            initial_capital=initial_capital
        )
        
        return self.benchmark_comparator.compare_to_benchmark(
            equity_curve=equity_curve,
            benchmark_name=benchmark_name,
            period=period
        )
    
    def generate_complete_report(
        self,
        account_id: str,
        trading_mode: TradingMode,
        period: AnalyticsPeriod,
        benchmark_name: Optional[str] = "NIFTY 50",
        initial_capital: float = 1000000.0
    ) -> AnalyticsReport:
        """
        Generate complete analytics report with all metrics and charts
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            period: Time period
            benchmark_name: Benchmark for comparison (optional)
            initial_capital: Starting capital
            
        Returns:
            Complete AnalyticsReport
        """
        # Get performance summary
        performance_summary = self.get_performance_metrics(
            account_id=account_id,
            trading_mode=trading_mode,
            period=period,
            initial_capital=initial_capital
        )
        
        # Get trade statistics
        trade_statistics = self.get_trade_analysis(
            account_id=account_id,
            trading_mode=trading_mode,
            period=period
        )
        
        # Get equity curve
        equity_curve = self.get_equity_curve(
            account_id=account_id,
            trading_mode=trading_mode,
            start_date=period.start_date,
            end_date=period.end_date,
            initial_capital=initial_capital
        )
        
        # Calculate drawdown periods
        drawdown_periods = self.performance_calculator.calculate_drawdown_analysis(
            equity_curve=equity_curve
        )
        
        # Get benchmark comparison if requested
        benchmark_comparison = None
        if benchmark_name:
            benchmark_comparison = self.compare_to_benchmark(
                account_id=account_id,
                trading_mode=trading_mode,
                period=period,
                benchmark_name=benchmark_name,
                initial_capital=initial_capital
            )
        
        # Generate charts
        charts = self._generate_all_charts(
            equity_curve=equity_curve,
            trade_statistics=trade_statistics,
            performance_summary=performance_summary
        )
        
        return AnalyticsReport(
            account_id=account_id,
            trading_mode=trading_mode.value,
            period=period,
            performance_summary=performance_summary,
            trade_statistics=trade_statistics,
            equity_curve=equity_curve,
            drawdown_periods=drawdown_periods,
            benchmark_comparison=benchmark_comparison,
            charts=charts
        )
    
    def export_report_csv(self, report: AnalyticsReport) -> BytesIO:
        """
        Export analytics report as CSV
        
        Args:
            report: AnalyticsReport to export
            
        Returns:
            BytesIO buffer with CSV data
        """
        output = BytesIO()
        output.write(b'\xef\xbb\xbf')  # UTF-8 BOM
        
        writer = csv.writer(output.buffer if hasattr(output, 'buffer') else output)
        
        # Write summary section
        writer.writerow(['Analytics Report'])
        writer.writerow(['Account ID', report.account_id])
        writer.writerow(['Trading Mode', report.trading_mode])
        writer.writerow(['Period', f"{report.period.start_date} to {report.period.end_date}"])
        writer.writerow(['Generated At', report.generated_at.isoformat()])
        writer.writerow([])
        
        # Write performance metrics
        writer.writerow(['Performance Metrics'])
        metrics = report.performance_summary.metrics
        writer.writerow(['Total Return (%)', f"{metrics.total_return:.2f}"])
        writer.writerow(['Annualized Return (%)', f"{metrics.annualized_return:.2f}"])
        writer.writerow(['Max Drawdown (%)', f"{metrics.max_drawdown:.2f}"])
        writer.writerow(['Sharpe Ratio', f"{metrics.sharpe_ratio:.2f}"])
        writer.writerow(['Sortino Ratio', f"{metrics.sortino_ratio:.2f}"])
        writer.writerow(['Win Rate (%)', f"{metrics.win_rate:.2f}"])
        writer.writerow(['Profit Factor', f"{metrics.profit_factor:.2f}"])
        writer.writerow(['Total Trades', metrics.total_trades])
        writer.writerow(['Winning Trades', metrics.winning_trades])
        writer.writerow(['Losing Trades', metrics.losing_trades])
        writer.writerow(['Total P&L (₹)', f"{metrics.total_pnl:.2f}"])
        writer.writerow([])
        
        # Write trade statistics
        writer.writerow(['Trade Statistics'])
        stats = report.trade_statistics
        writer.writerow(['Average Holding Time (hours)', f"{stats.average_holding_time:.2f}"])
        writer.writerow(['Consecutive Wins', stats.consecutive_wins])
        writer.writerow(['Consecutive Losses', stats.consecutive_losses])
        writer.writerow(['Win/Loss Ratio', f"{stats.win_loss_ratio:.2f}"])
        writer.writerow([])
        
        # Write equity curve
        writer.writerow(['Equity Curve'])
        writer.writerow(['Timestamp', 'Equity', 'Drawdown (%)', 'Daily Return (%)'])
        for point in report.equity_curve:
            writer.writerow([
                point.timestamp.isoformat(),
                f"{point.equity:.2f}",
                f"{point.drawdown:.2f}",
                f"{point.daily_return:.2f}"
            ])
        
        output.seek(0)
        return output
    
    def _generate_all_charts(
        self,
        equity_curve: List[EquityPoint],
        trade_statistics: TradeStatistics,
        performance_summary: PerformanceSummary
    ) -> List[ChartData]:
        """Generate all chart data"""
        charts = []
        
        # Equity curve chart
        charts.append(self.chart_generator.generate_equity_curve_chart(equity_curve))
        
        # Drawdown chart
        charts.append(self.chart_generator.generate_drawdown_chart(equity_curve))
        
        # Get trade details for distribution chart
        trade_details = self.trade_analyzer.get_trade_details(
            account_id=performance_summary.account_id,
            trading_mode=TradingMode(performance_summary.trading_mode),
            period=performance_summary.period
        )
        
        # Win/loss distribution
        charts.append(self.chart_generator.generate_win_loss_distribution(trade_details))
        
        # Profit by time heatmap
        charts.append(self.chart_generator.generate_profit_by_time_heatmap(
            profit_by_time=trade_statistics.profit_by_time_of_day,
            profit_by_day=trade_statistics.profit_by_day_of_week
        ))
        
        # Strategy comparison
        if performance_summary.strategy_breakdown:
            charts.append(self.chart_generator.generate_strategy_comparison_chart(
                strategy_breakdown=performance_summary.strategy_breakdown
            ))
        
        # Monthly returns
        charts.append(self.chart_generator.generate_monthly_returns_chart(equity_curve))
        
        # Cumulative P&L
        charts.append(self.chart_generator.generate_cumulative_pnl_chart(trade_details))
        
        return charts
