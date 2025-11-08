"""
Subscription Manager

Manages market data subscriptions and tracks which strategies need which symbols/timeframes.
"""
from typing import Dict, Set, List, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """Represents a subscription to market data"""
    subscriber_id: str  # Strategy ID or client ID
    symbol: str
    timeframes: Set[str] = field(default_factory=set)
    exchange: str = 'NSE'  # NSE, BSE, NFO, MCX
    
    def add_timeframe(self, timeframe: str) -> None:
        """Add a timeframe to this subscription"""
        self.timeframes.add(timeframe)
    
    def remove_timeframe(self, timeframe: str) -> None:
        """Remove a timeframe from this subscription"""
        self.timeframes.discard(timeframe)
    
    def has_timeframe(self, timeframe: str) -> bool:
        """Check if subscription includes a timeframe"""
        return timeframe in self.timeframes


class SubscriptionManager:
    """Manages market data subscriptions"""
    
    def __init__(self):
        # Map of symbol -> set of subscriber IDs
        self.symbol_subscribers: Dict[str, Set[str]] = {}
        
        # Map of subscriber_id -> Subscription
        self.subscriptions: Dict[str, Subscription] = {}
        
        # Map of symbol -> exchange
        self.symbol_exchanges: Dict[str, str] = {}
    
    def subscribe(
        self,
        subscriber_id: str,
        symbol: str,
        timeframes: List[str],
        exchange: str = 'NSE'
    ) -> None:
        """
        Subscribe to market data for a symbol.
        
        Args:
            subscriber_id: Unique ID of the subscriber (strategy or client)
            symbol: Symbol to subscribe to
            timeframes: List of timeframes to subscribe to
            exchange: Exchange segment (NSE, BSE, NFO, MCX)
        """
        logger.info(
            f"Subscriber {subscriber_id} subscribing to {symbol} "
            f"on {exchange} for timeframes {timeframes}"
        )
        
        # Create or update subscription
        sub_key = f"{subscriber_id}:{symbol}"
        if sub_key not in self.subscriptions:
            self.subscriptions[sub_key] = Subscription(
                subscriber_id=subscriber_id,
                symbol=symbol,
                exchange=exchange
            )
        
        subscription = self.subscriptions[sub_key]
        for timeframe in timeframes:
            subscription.add_timeframe(timeframe)
        
        # Track symbol subscribers
        if symbol not in self.symbol_subscribers:
            self.symbol_subscribers[symbol] = set()
        self.symbol_subscribers[symbol].add(subscriber_id)
        
        # Track symbol exchange
        self.symbol_exchanges[symbol] = exchange
    
    def unsubscribe(
        self,
        subscriber_id: str,
        symbol: Optional[str] = None,
        timeframes: Optional[List[str]] = None
    ) -> None:
        """
        Unsubscribe from market data.
        
        Args:
            subscriber_id: Unique ID of the subscriber
            symbol: Symbol to unsubscribe from (None = all symbols)
            timeframes: Timeframes to unsubscribe from (None = all timeframes)
        """
        if symbol is None:
            # Unsubscribe from all symbols
            keys_to_remove = [
                key for key in self.subscriptions.keys()
                if key.startswith(f"{subscriber_id}:")
            ]
            for key in keys_to_remove:
                subscription = self.subscriptions[key]
                self._remove_subscription(subscription)
            
            logger.info(f"Subscriber {subscriber_id} unsubscribed from all symbols")
        else:
            # Unsubscribe from specific symbol
            sub_key = f"{subscriber_id}:{symbol}"
            if sub_key in self.subscriptions:
                subscription = self.subscriptions[sub_key]
                
                if timeframes is None:
                    # Remove entire subscription
                    self._remove_subscription(subscription)
                    logger.info(f"Subscriber {subscriber_id} unsubscribed from {symbol}")
                else:
                    # Remove specific timeframes
                    for timeframe in timeframes:
                        subscription.remove_timeframe(timeframe)
                    
                    # If no timeframes left, remove subscription
                    if not subscription.timeframes:
                        self._remove_subscription(subscription)
                    
                    logger.info(
                        f"Subscriber {subscriber_id} unsubscribed from {symbol} "
                        f"timeframes {timeframes}"
                    )
    
    def _remove_subscription(self, subscription: Subscription) -> None:
        """Remove a subscription completely"""
        sub_key = f"{subscription.subscriber_id}:{subscription.symbol}"
        
        # Remove from subscriptions
        if sub_key in self.subscriptions:
            del self.subscriptions[sub_key]
        
        # Remove from symbol subscribers
        if subscription.symbol in self.symbol_subscribers:
            self.symbol_subscribers[subscription.symbol].discard(subscription.subscriber_id)
            
            # If no more subscribers for this symbol, remove it
            if not self.symbol_subscribers[subscription.symbol]:
                del self.symbol_subscribers[subscription.symbol]
                if subscription.symbol in self.symbol_exchanges:
                    del self.symbol_exchanges[subscription.symbol]
    
    def get_subscribed_symbols(self) -> List[str]:
        """Get list of all symbols with active subscriptions"""
        return list(self.symbol_subscribers.keys())
    
    def get_subscribers_for_symbol(self, symbol: str) -> Set[str]:
        """Get all subscriber IDs for a symbol"""
        return self.symbol_subscribers.get(symbol, set()).copy()
    
    def get_symbol_exchange(self, symbol: str) -> Optional[str]:
        """Get the exchange for a symbol"""
        return self.symbol_exchanges.get(symbol)
    
    def get_subscriber_subscriptions(self, subscriber_id: str) -> List[Subscription]:
        """Get all subscriptions for a subscriber"""
        return [
            sub for sub in self.subscriptions.values()
            if sub.subscriber_id == subscriber_id
        ]
    
    def is_subscribed(self, subscriber_id: str, symbol: str, timeframe: Optional[str] = None) -> bool:
        """Check if a subscriber is subscribed to a symbol/timeframe"""
        sub_key = f"{subscriber_id}:{symbol}"
        if sub_key not in self.subscriptions:
            return False
        
        if timeframe is None:
            return True
        
        return self.subscriptions[sub_key].has_timeframe(timeframe)
    
    def get_subscription_count(self) -> int:
        """Get total number of active subscriptions"""
        return len(self.subscriptions)
    
    def get_symbol_count(self) -> int:
        """Get number of unique symbols subscribed to"""
        return len(self.symbol_subscribers)
    
    def get_stats(self) -> Dict:
        """Get subscription statistics"""
        return {
            'total_subscriptions': self.get_subscription_count(),
            'unique_symbols': self.get_symbol_count(),
            'unique_subscribers': len(set(sub.subscriber_id for sub in self.subscriptions.values())),
            'symbols_by_exchange': self._get_symbols_by_exchange()
        }
    
    def _get_symbols_by_exchange(self) -> Dict[str, int]:
        """Get count of symbols by exchange"""
        exchange_counts = {}
        for exchange in self.symbol_exchanges.values():
            exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1
        return exchange_counts
