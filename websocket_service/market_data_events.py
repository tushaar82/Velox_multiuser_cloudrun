"""
Market Data WebSocket Events - Handles chart subscriptions and real-time market data updates.
"""
import logging
from typing import List, Dict, Any, Optional
from flask import request
from flask_socketio import emit

from websocket_service.websocket_server import (
    socketio, authenticated_only, subscribe_to_room, 
    unsubscribe_from_room, broadcast_to_room, publish_broadcast
)
from websocket_service.room_manager import RoomManager
from market_data_engine.models import Tick, Candle, IndicatorValue

logger = logging.getLogger(__name__)


@socketio.on('subscribe_chart')
@authenticated_only
def handle_subscribe_chart(data: Dict[str, Any]):
    """
    Handle chart subscription request.
    Client subscribes to real-time updates for a specific symbol and timeframe.
    
    Expected data format:
    {
        'symbol': 'RELIANCE',
        'timeframe': '5m',
        'indicators': ['SMA_20', 'RSI_14']  # Optional
    }
    """
    try:
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        indicators = data.get('indicators', [])
        
        if not symbol or not timeframe:
            emit('error', {
                'message': 'Missing required fields: symbol and timeframe'
            })
            return
        
        # Get room name for this chart
        room_name = RoomManager.get_chart_room(symbol, timeframe)
        
        # Subscribe to room
        subscribe_to_room(room_name)
        
        # Load and send historical data
        historical_candles = _load_historical_candles(symbol, timeframe, count=100)
        forming_candle = _get_forming_candle(symbol, timeframe)
        indicator_values = _load_indicator_values(symbol, timeframe, indicators)
        
        emit('chart_subscribed', {
            'symbol': symbol,
            'timeframe': timeframe,
            'historical_candles': [c.to_dict() for c in historical_candles],
            'forming_candle': forming_candle.to_dict() if forming_candle else None,
            'indicators': {ind: val.to_dict() for ind, val in indicator_values.items()}
        })
        
        logger.info(f"User {request.user_id} subscribed to chart {symbol}:{timeframe}")
        
    except Exception as e:
        logger.error(f"Error in subscribe_chart: {e}")
        emit('error', {'message': f'Failed to subscribe to chart: {str(e)}'})


@socketio.on('unsubscribe_chart')
@authenticated_only
def handle_unsubscribe_chart(data: Dict[str, Any]):
    """
    Handle chart unsubscription request.
    
    Expected data format:
    {
        'symbol': 'RELIANCE',
        'timeframe': '5m'
    }
    """
    try:
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        
        if not symbol or not timeframe:
            emit('error', {
                'message': 'Missing required fields: symbol and timeframe'
            })
            return
        
        # Get room name for this chart
        room_name = RoomManager.get_chart_room(symbol, timeframe)
        
        # Unsubscribe from room
        unsubscribe_from_room(room_name)
        
        emit('chart_unsubscribed', {
            'symbol': symbol,
            'timeframe': timeframe
        })
        
        logger.info(f"User {request.user_id} unsubscribed from chart {symbol}:{timeframe}")
        
    except Exception as e:
        logger.error(f"Error in unsubscribe_chart: {e}")
        emit('error', {'message': f'Failed to unsubscribe from chart: {str(e)}'})


def broadcast_tick_update(tick: Tick, timeframes: List[str]):
    """
    Broadcast tick update to all subscribed clients.
    Called by market data engine when new tick arrives.
    
    Args:
        tick: Tick data
        timeframes: List of timeframes affected by this tick
    """
    tick_data = tick.to_dict()
    
    # Broadcast to all chart rooms for this symbol across all timeframes
    for timeframe in timeframes:
        room_name = RoomManager.get_chart_room(tick.symbol, timeframe)
        
        # Use Redis pub/sub for cross-instance broadcasting
        publish_broadcast(
            event='tick_update',
            payload={
                'symbol': tick.symbol,
                'timeframe': timeframe,
                'tick': tick_data
            },
            room=room_name
        )
    
    logger.debug(f"Broadcasted tick update for {tick.symbol} to {len(timeframes)} timeframes")


def broadcast_candle_update(candle: Candle):
    """
    Broadcast forming candle update to all subscribed clients.
    Called by market data engine when forming candle is updated.
    
    Args:
        candle: Updated forming candle
    """
    room_name = RoomManager.get_chart_room(candle.symbol, candle.timeframe)
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='candle_update',
        payload={
            'symbol': candle.symbol,
            'timeframe': candle.timeframe,
            'candle': candle.to_dict()
        },
        room=room_name
    )
    
    logger.debug(f"Broadcasted candle update for {candle.symbol}:{candle.timeframe}")


def broadcast_candle_complete(candle: Candle):
    """
    Broadcast candle completion to all subscribed clients.
    Called by market data engine when a candle period completes.
    
    Args:
        candle: Completed candle
    """
    room_name = RoomManager.get_chart_room(candle.symbol, candle.timeframe)
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='candle_complete',
        payload={
            'symbol': candle.symbol,
            'timeframe': candle.timeframe,
            'candle': candle.to_dict()
        },
        room=room_name
    )
    
    logger.info(f"Broadcasted candle completion for {candle.symbol}:{candle.timeframe}")


def broadcast_indicator_update(indicator: IndicatorValue):
    """
    Broadcast indicator update to all subscribed clients.
    Called by market data engine when indicator is recalculated.
    
    Args:
        indicator: Updated indicator value
    """
    room_name = RoomManager.get_chart_room(indicator.symbol, indicator.timeframe)
    
    # Use Redis pub/sub for cross-instance broadcasting
    publish_broadcast(
        event='indicator_update',
        payload={
            'symbol': indicator.symbol,
            'timeframe': indicator.timeframe,
            'indicator': indicator.to_dict()
        },
        room=room_name
    )
    
    logger.debug(f"Broadcasted indicator update for {indicator.symbol}:{indicator.timeframe} - {indicator.indicator_type}")


def _load_historical_candles(symbol: str, timeframe: str, count: int = 100) -> List[Candle]:
    """
    Load historical candles from storage.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        count: Number of candles to load
        
    Returns:
        List of historical candles
    """
    # TODO: Integrate with market data engine storage
    # For now, return empty list
    # This should call market_data_engine.storage.get_historical_candles()
    from market_data_engine.storage import CandleStorage
    
    try:
        storage = CandleStorage()
        candles = storage.get_recent_candles(symbol, timeframe, count)
        return candles
    except Exception as e:
        logger.error(f"Error loading historical candles: {e}")
        return []


def _get_forming_candle(symbol: str, timeframe: str) -> Optional[Candle]:
    """
    Get current forming candle from Redis.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Forming candle or None
    """
    # TODO: Integrate with market data engine
    # This should call market_data_engine.candle_manager.get_forming_candle()
    from market_data_engine.candle_manager import CandleManager
    
    try:
        candle_manager = CandleManager()
        forming_candle = candle_manager.get_forming_candle(symbol, timeframe)
        return forming_candle
    except Exception as e:
        logger.error(f"Error getting forming candle: {e}")
        return None


def _load_indicator_values(symbol: str, timeframe: str, 
                          indicators: List[str]) -> Dict[str, IndicatorValue]:
    """
    Load current indicator values.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        indicators: List of indicator names (e.g., ['SMA_20', 'RSI_14'])
        
    Returns:
        Dictionary of indicator name to IndicatorValue
    """
    # TODO: Integrate with market data engine
    # This should call market_data_engine.indicators.get_indicator_values()
    result = {}
    
    try:
        from market_data_engine.indicators import IndicatorCalculator
        
        calculator = IndicatorCalculator()
        for indicator_name in indicators:
            # Parse indicator name (e.g., 'SMA_20' -> type='SMA', period=20)
            parts = indicator_name.split('_')
            if len(parts) >= 2:
                indicator_type = parts[0]
                params = {'period': int(parts[1])} if parts[1].isdigit() else {}
                
                indicator_value = calculator.get_indicator_value(
                    symbol, timeframe, indicator_type, params
                )
                if indicator_value:
                    result[indicator_name] = indicator_value
                    
    except Exception as e:
        logger.error(f"Error loading indicator values: {e}")
    
    return result
