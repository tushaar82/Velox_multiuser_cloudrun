"""
Strategy Plugin Manager

Manages loading and discovery of pre-built strategy modules.
"""

import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Type, Any, Optional

from strategy_workers.strategy_interface import IStrategy

logger = logging.getLogger(__name__)


class StrategyPluginManager:
    """Manages strategy plugin discovery and loading"""
    
    def __init__(self, plugin_dir: str = "strategy_workers/strategies"):
        """
        Initialize plugin manager.
        
        Args:
            plugin_dir: Directory containing strategy plugins
        """
        self.plugin_dir = Path(plugin_dir)
        self.strategies: Dict[str, Type[IStrategy]] = {}
        self.strategy_configs: Dict[str, Dict[str, Any]] = {}
    
    def discover_plugins(self) -> List[Dict[str, Any]]:
        """
        Scan plugin directory and discover all available strategies.
        
        Returns:
            List of strategy configuration dictionaries
        """
        plugins = []
        
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist")
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return plugins
        
        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir() and not plugin_path.name.startswith('_'):
                config_file = plugin_path / 'config.json'
                
                if config_file.exists():
                    try:
                        with open(config_file) as f:
                            config = json.load(f)
                        
                        # Validate required fields
                        if self._validate_config(config):
                            plugins.append(config)
                            self._load_strategy(plugin_path, config)
                            logger.info(f"Discovered strategy: {config['name']}")
                        else:
                            logger.warning(f"Invalid config for {plugin_path.name}")
                            
                    except Exception as e:
                        logger.error(f"Failed to load config from {config_file}: {e}")
        
        logger.info(f"Discovered {len(plugins)} strategy plugins")
        return plugins
    
    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate strategy configuration.
        
        Args:
            config: Strategy configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['name', 'version', 'description', 'parameters']
        return all(field in config for field in required_fields)
    
    def _load_strategy(self, path: Path, config: Dict[str, Any]) -> None:
        """
        Dynamically import and load strategy module.
        
        Args:
            path: Path to strategy plugin directory
            config: Strategy configuration
        """
        try:
            strategy_file = path / 'strategy.py'
            
            if not strategy_file.exists():
                logger.error(f"Strategy file not found: {strategy_file}")
                return
            
            # Dynamically import the module
            module_name = f"strategies.{path.name}.strategy"
            spec = importlib.util.spec_from_file_location(module_name, strategy_file)
            
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load spec for {strategy_file}")
                return
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find IStrategy implementation
            strategy_class = None
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and 
                    issubclass(item, IStrategy) and 
                    item != IStrategy):
                    strategy_class = item
                    break
            
            if strategy_class:
                self.strategies[config['name']] = strategy_class
                self.strategy_configs[config['name']] = config
                logger.info(f"Loaded strategy class: {config['name']}")
            else:
                logger.error(f"No IStrategy implementation found in {strategy_file}")
                
        except Exception as e:
            logger.error(f"Failed to load strategy from {path}: {e}")
    
    def get_strategy(self, name: str) -> Optional[Type[IStrategy]]:
        """
        Get strategy class by name.
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy class if found, None otherwise
        """
        return self.strategies.get(name)
    
    def get_strategy_config(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get strategy configuration by name.
        
        Args:
            name: Strategy name
            
        Returns:
            Strategy configuration if found, None otherwise
        """
        return self.strategy_configs.get(name)
    
    def list_strategies(self) -> List[str]:
        """
        List all available strategy names.
        
        Returns:
            List of strategy names
        """
        return list(self.strategies.keys())
    
    def get_all_configs(self) -> List[Dict[str, Any]]:
        """
        Get all strategy configurations.
        
        Returns:
            List of strategy configurations
        """
        return list(self.strategy_configs.values())
    
    def reload_plugins(self) -> None:
        """
        Reload all strategy plugins.
        
        Useful for development or when strategies are updated.
        """
        self.strategies.clear()
        self.strategy_configs.clear()
        self.discover_plugins()
        logger.info("Reloaded all strategy plugins")
    
    def validate_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate strategy parameters against configuration.
        
        Args:
            strategy_name: Name of the strategy
            parameters: Parameters to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        config = self.get_strategy_config(strategy_name)
        
        if not config:
            return False, f"Strategy '{strategy_name}' not found"
        
        param_defs = config.get('parameters', [])
        
        for param_def in param_defs:
            param_name = param_def['name']
            param_type = param_def['type']
            
            # Check if required parameter is present
            if param_def.get('required', False) and param_name not in parameters:
                return False, f"Required parameter '{param_name}' is missing"
            
            # Validate parameter type and range
            if param_name in parameters:
                value = parameters[param_name]
                
                # Type validation
                if param_type == 'integer' and not isinstance(value, int):
                    return False, f"Parameter '{param_name}' must be an integer"
                elif param_type == 'float' and not isinstance(value, (int, float)):
                    return False, f"Parameter '{param_name}' must be a number"
                elif param_type == 'string' and not isinstance(value, str):
                    return False, f"Parameter '{param_name}' must be a string"
                elif param_type == 'boolean' and not isinstance(value, bool):
                    return False, f"Parameter '{param_name}' must be a boolean"
                
                # Range validation for numeric types
                if param_type in ['integer', 'float']:
                    if 'min' in param_def and value < param_def['min']:
                        return False, f"Parameter '{param_name}' must be >= {param_def['min']}"
                    if 'max' in param_def and value > param_def['max']:
                        return False, f"Parameter '{param_name}' must be <= {param_def['max']}"
        
        return True, None
