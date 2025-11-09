"""
Data Quality Checker

Validates historical data completeness and quality.
"""
import sys
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """Data quality report"""
    file_path: str
    symbol: str
    total_records: int
    start_time: datetime
    end_time: datetime
    duration_hours: float
    gaps: List[Tuple[datetime, datetime, float]]
    duplicates: int
    invalid_prices: int
    invalid_volumes: int
    missing_fields: int
    quality_score: float
    issues: List[str]


class DataQualityChecker:
    """
    Checks quality of historical data.
    
    Validates:
    - Completeness (no gaps)
    - Data integrity (valid prices, volumes)
    - Consistency (no duplicates)
    """
    
    def __init__(self):
        self.max_gap_seconds = 60  # Maximum acceptable gap
    
    def check_file(self, file_path: str) -> DataQualityReport:
        """
        Check data quality of a CSV file.
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Data quality report
        """
        logger.info(f"Checking {file_path}...")
        
        records = []
        missing_fields = 0
        invalid_prices = 0
        invalid_volumes = 0
        
        # Read file
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    # Check for missing fields
                    required_fields = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']
                    if not all(field in row for field in required_fields):
                        missing_fields += 1
                        continue
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.fromisoformat(row['timestamp'])
                    except:
                        missing_fields += 1
                        continue
                    
                    # Parse prices
                    try:
                        open_price = float(row['open'])
                        high_price = float(row['high'])
                        low_price = float(row['low'])
                        close_price = float(row['close'])
                        
                        # Validate price relationships
                        if not (low_price <= open_price <= high_price and
                                low_price <= close_price <= high_price):
                            invalid_prices += 1
                            continue
                        
                        # Check for negative or zero prices
                        if any(p <= 0 for p in [open_price, high_price, low_price, close_price]):
                            invalid_prices += 1
                            continue
                    except:
                        invalid_prices += 1
                        continue
                    
                    # Parse volume
                    try:
                        volume = int(row['volume'])
                        if volume < 0:
                            invalid_volumes += 1
                            continue
                    except:
                        invalid_volumes += 1
                        continue
                    
                    records.append({
                        'timestamp': timestamp,
                        'symbol': row['symbol'],
                        'open': open_price,
                        'high': high_price,
                        'low': low_price,
                        'close': close_price,
                        'volume': volume
                    })
        
        except Exception as e:
            logger.error(f"Error reading file: {e}", exc_info=True)
            return None
        
        if not records:
            logger.error("No valid records found")
            return None
        
        # Sort by timestamp
        records.sort(key=lambda r: r['timestamp'])
        
        # Extract info
        symbol = records[0]['symbol']
        start_time = records[0]['timestamp']
        end_time = records[-1]['timestamp']
        duration_hours = (end_time - start_time).total_seconds() / 3600
        
        # Check for gaps
        gaps = self._find_gaps(records)
        
        # Check for duplicates
        duplicates = self._find_duplicates(records)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(
            total_records=len(records),
            gaps=len(gaps),
            duplicates=duplicates,
            invalid_prices=invalid_prices,
            invalid_volumes=invalid_volumes,
            missing_fields=missing_fields
        )
        
        # Generate issues list
        issues = []
        if gaps:
            issues.append(f"{len(gaps)} gaps found (max gap: {max(g[2] for g in gaps):.1f} seconds)")
        if duplicates > 0:
            issues.append(f"{duplicates} duplicate timestamps")
        if invalid_prices > 0:
            issues.append(f"{invalid_prices} invalid price records")
        if invalid_volumes > 0:
            issues.append(f"{invalid_volumes} invalid volume records")
        if missing_fields > 0:
            issues.append(f"{missing_fields} records with missing fields")
        
        report = DataQualityReport(
            file_path=file_path,
            symbol=symbol,
            total_records=len(records),
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            gaps=gaps,
            duplicates=duplicates,
            invalid_prices=invalid_prices,
            invalid_volumes=invalid_volumes,
            missing_fields=missing_fields,
            quality_score=quality_score,
            issues=issues
        )
        
        return report
    
    def _find_gaps(self, records: List[Dict]) -> List[Tuple[datetime, datetime, float]]:
        """Find gaps in data"""
        gaps = []
        
        for i in range(1, len(records)):
            prev_time = records[i-1]['timestamp']
            curr_time = records[i]['timestamp']
            
            gap_seconds = (curr_time - prev_time).total_seconds()
            
            if gap_seconds > self.max_gap_seconds:
                gaps.append((prev_time, curr_time, gap_seconds))
        
        return gaps
    
    def _find_duplicates(self, records: List[Dict]) -> int:
        """Find duplicate timestamps"""
        timestamps = [r['timestamp'] for r in records]
        return len(timestamps) - len(set(timestamps))
    
    def _calculate_quality_score(
        self,
        total_records: int,
        gaps: int,
        duplicates: int,
        invalid_prices: int,
        invalid_volumes: int,
        missing_fields: int
    ) -> float:
        """Calculate quality score (0-100)"""
        if total_records == 0:
            return 0.0
        
        # Start with perfect score
        score = 100.0
        
        # Deduct for issues
        score -= (gaps * 2)  # 2 points per gap
        score -= (duplicates * 1)  # 1 point per duplicate
        score -= (invalid_prices * 5)  # 5 points per invalid price
        score -= (invalid_volumes * 2)  # 2 points per invalid volume
        score -= (missing_fields * 3)  # 3 points per missing field
        
        return max(0.0, min(100.0, score))
    
    def check_directory(self, directory: str) -> List[DataQualityReport]:
        """Check all CSV files in directory"""
        reports = []
        
        for file_path in Path(directory).glob("*.csv"):
            report = self.check_file(str(file_path))
            if report:
                reports.append(report)
        
        return reports
    
    def print_report(self, report: DataQualityReport) -> None:
        """Print quality report"""
        print(f"\n{'='*80}")
        print(f"Data Quality Report: {report.file_path}")
        print(f"{'='*80}")
        print(f"Symbol: {report.symbol}")
        print(f"Records: {report.total_records}")
        print(f"Time Range: {report.start_time} to {report.end_time}")
        print(f"Duration: {report.duration_hours:.2f} hours")
        print(f"\nQuality Score: {report.quality_score:.1f}/100")
        
        if report.issues:
            print(f"\nIssues Found:")
            for issue in report.issues:
                print(f"  - {issue}")
        else:
            print(f"\nNo issues found - data quality is excellent!")
        
        if report.gaps:
            print(f"\nTop 5 Largest Gaps:")
            sorted_gaps = sorted(report.gaps, key=lambda g: g[2], reverse=True)[:5]
            for start, end, seconds in sorted_gaps:
                print(f"  - {start} to {end} ({seconds:.1f} seconds)")
    
    def print_summary(self, reports: List[DataQualityReport]) -> None:
        """Print summary of multiple reports"""
        print(f"\n{'='*80}")
        print(f"Data Quality Summary ({len(reports)} files)")
        print(f"{'='*80}")
        
        if not reports:
            print("No reports to summarize")
            return
        
        avg_score = sum(r.quality_score for r in reports) / len(reports)
        total_records = sum(r.total_records for r in reports)
        total_issues = sum(len(r.issues) for r in reports)
        
        print(f"Average Quality Score: {avg_score:.1f}/100")
        print(f"Total Records: {total_records:,}")
        print(f"Total Issues: {total_issues}")
        
        print(f"\nFiles by Quality:")
        sorted_reports = sorted(reports, key=lambda r: r.quality_score, reverse=True)
        for report in sorted_reports:
            status = "✓" if report.quality_score >= 90 else "⚠" if report.quality_score >= 70 else "✗"
            print(f"  {status} {report.symbol}: {report.quality_score:.1f}/100 ({len(report.issues)} issues)")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Data Quality Checker')
    parser.add_argument('path', help='File or directory to check')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    
    args = parser.parse_args()
    
    checker = DataQualityChecker()
    
    path = Path(args.path)
    
    if path.is_file():
        # Check single file
        report = checker.check_file(str(path))
        if report:
            checker.print_report(report)
    
    elif path.is_dir():
        # Check directory
        reports = checker.check_directory(str(path))
        
        if args.summary:
            checker.print_summary(reports)
        else:
            for report in reports:
                checker.print_report(report)
            checker.print_summary(reports)
    
    else:
        print(f"Error: {args.path} not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
