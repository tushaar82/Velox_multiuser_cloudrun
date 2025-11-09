"""
Replay CLI Tool

Command-line tool for running strategies in replay mode without UI.
"""
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from market_data_engine.simulator import MarketDataSimulator
from market_data_engine.replay_manager import ReplaySessionManager
from strategy_workers.strategy_orchestrator import StrategyOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReplayCLI:
    """
    CLI tool for replay testing.
    
    Runs strategies against historical data and outputs results.
    """
    
    def __init__(self):
        self.simulator = MarketDataSimulator()
        self.session_manager = ReplaySessionManager()
        self.session_manager.attach_simulator(self.simulator)
        self.orchestrator = None
    
    def load_data(self, data_files: List[str]) -> bool:
        """
        Load historical data from CSV files.
        
        Args:
            data_files: List of CSV file paths
        
        Returns:
            True if loaded successfully
        """
        logger.info(f"Loading {len(data_files)} data files...")
        
        for file_path in data_files:
            # Extract symbol from filename
            symbol = Path(file_path).stem.split('_')[0]
            
            count = self.simulator.load_csv_data(symbol, file_path)
            if count == 0:
                logger.error(f"Failed to load data from {file_path}")
                return False
        
        logger.info("Data loaded successfully")
        return True
    
    def run_replay(
        self,
        strategy_config: Dict[str, Any],
        speed: float = 10.0,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        Run replay with strategy.
        
        Args:
            strategy_config: Strategy configuration
            speed: Replay speed multiplier
            output_file: Output file for results
        
        Returns:
            Replay results
        """
        logger.info(f"Starting replay at {speed}x speed...")
        
        # Set speed
        self.simulator.set_speed(speed)
        
        # Start replay
        symbols = strategy_config.get('symbols', [])
        if not self.simulator.start_replay(symbols):
            logger.error("Failed to start replay")
            return {}
        
        # Wait for completion
        while self.simulator.state.value != 'stopped':
            import time
            time.sleep(1)
        
        logger.info("Replay completed")
        
        # Get results
        results = {
            'completed_at': datetime.now().isoformat(),
            'strategy': strategy_config,
            'performance': {}  # Would be populated by strategy
        }
        
        # Save results
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {output_file}")
        
        return results
    
    def run_batch(self, config_file: str) -> List[Dict[str, Any]]:
        """
        Run batch of replays from config file.
        
        Args:
            config_file: Path to batch config JSON file
        
        Returns:
            List of results
        """
        logger.info(f"Running batch from {config_file}...")
        
        with open(config_file, 'r') as f:
            batch_config = json.load(f)
        
        results = []
        
        for i, test_config in enumerate(batch_config.get('tests', [])):
            logger.info(f"Running test {i+1}/{len(batch_config['tests'])}: {test_config.get('name')}")
            
            # Load data
            if not self.load_data(test_config['data_files']):
                logger.error(f"Failed to load data for test {i+1}")
                continue
            
            # Run replay
            result = self.run_replay(
                strategy_config=test_config['strategy'],
                speed=test_config.get('speed', 10.0),
                output_file=test_config.get('output_file')
            )
            
            results.append({
                'test_name': test_config.get('name'),
                'result': result
            })
        
        logger.info(f"Batch completed: {len(results)} tests run")
        return results


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Replay CLI Tool')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run single replay')
    run_parser.add_argument('--data', nargs='+', required=True, help='Data files')
    run_parser.add_argument('--strategy', required=True, help='Strategy config JSON file')
    run_parser.add_argument('--speed', type=float, default=10.0, help='Replay speed')
    run_parser.add_argument('--output', help='Output file for results')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Run batch of replays')
    batch_parser.add_argument('--config', required=True, help='Batch config JSON file')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List saved sessions')
    
    args = parser.parse_args()
    
    cli = ReplayCLI()
    
    if args.command == 'run':
        # Load strategy config
        with open(args.strategy, 'r') as f:
            strategy_config = json.load(f)
        
        # Load data
        if not cli.load_data(args.data):
            sys.exit(1)
        
        # Run replay
        results = cli.run_replay(
            strategy_config=strategy_config,
            speed=args.speed,
            output_file=args.output
        )
        
        print(json.dumps(results, indent=2))
    
    elif args.command == 'batch':
        results = cli.run_batch(args.config)
        print(f"Completed {len(results)} tests")
    
    elif args.command == 'list':
        sessions = cli.session_manager.list_sessions()
        print(f"Found {len(sessions)} saved sessions:")
        for session in sessions:
            print(f"  - {session['session_id']}: {session['name']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
