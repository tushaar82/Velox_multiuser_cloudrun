"""
Room Manager - Manages WebSocket room subscriptions and naming conventions.
"""
from typing import List


class RoomManager:
    """Manages WebSocket room naming and subscription logic."""
    
    @staticmethod
    def get_chart_room(symbol: str, timeframe: str) -> str:
        """
        Get room name for chart data subscription.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            
        Returns:
            Room name
        """
        return f"chart:{symbol}:{timeframe}"
    
    @staticmethod
    def get_account_room(account_id: str, trading_mode: str) -> str:
        """
        Get room name for account-specific updates.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode ('paper' or 'live')
            
        Returns:
            Room name
        """
        return f"account:{account_id}:{trading_mode}"
    
    @staticmethod
    def get_user_room(user_id: str) -> str:
        """
        Get room name for user-specific notifications.
        
        Args:
            user_id: User ID
            
        Returns:
            Room name
        """
        return f"user:{user_id}"
    
    @staticmethod
    def get_strategy_room(strategy_id: str) -> str:
        """
        Get room name for strategy-specific updates.
        
        Args:
            strategy_id: Strategy ID
            
        Returns:
            Room name
        """
        return f"strategy:{strategy_id}"
    
    @staticmethod
    def get_position_room(account_id: str, trading_mode: str) -> str:
        """
        Get room name for position updates.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode ('paper' or 'live')
            
        Returns:
            Room name
        """
        return f"positions:{account_id}:{trading_mode}"
    
    @staticmethod
    def get_order_room(account_id: str, trading_mode: str) -> str:
        """
        Get room name for order updates.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode ('paper' or 'live')
            
        Returns:
            Room name
        """
        return f"orders:{account_id}:{trading_mode}"
    
    @staticmethod
    def parse_chart_room(room_name: str) -> tuple:
        """
        Parse chart room name to extract symbol and timeframe.
        
        Args:
            room_name: Room name in format 'chart:SYMBOL:TIMEFRAME'
            
        Returns:
            Tuple of (symbol, timeframe)
        """
        parts = room_name.split(':')
        if len(parts) == 3 and parts[0] == 'chart':
            return parts[1], parts[2]
        return None, None
    
    @staticmethod
    def parse_account_room(room_name: str) -> tuple:
        """
        Parse account room name to extract account_id and trading_mode.
        
        Args:
            room_name: Room name in format 'account:ACCOUNT_ID:MODE'
            
        Returns:
            Tuple of (account_id, trading_mode)
        """
        parts = room_name.split(':')
        if len(parts) == 3 and parts[0] == 'account':
            return parts[1], parts[2]
        return None, None
    
    @staticmethod
    def get_all_chart_rooms_for_symbol(symbol: str, timeframes: List[str]) -> List[str]:
        """
        Get all chart room names for a symbol across multiple timeframes.
        
        Args:
            symbol: Trading symbol
            timeframes: List of timeframes
            
        Returns:
            List of room names
        """
        return [RoomManager.get_chart_room(symbol, tf) for tf in timeframes]
