# exchange/models/order.py
from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class Order:
    """
    Tüm borsalar için standartlaştırılmış bir emir (order) veri modeli.
    """
    def __init__(
        self,
        id: Optional[str],
        symbol: str,
        side: str,
        amount: float,
        price: Optional[float] = None, # <<< DEĞİŞİKLİK BURADA: None varsayılan değer olarak eklendi.
        status: str = 'unknown',       # <<< DEĞİŞİKLİK BURADA: status için varsayılan değer eklendi.
        order_type: Optional[str] = 'market',
        filled: Optional[float] = 0.0,
        average_price: Optional[float] = None,
        exchange_id: Optional[str] = None,
        timestamp_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        raw_data: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.symbol = symbol
        self.side = side.lower()
        self.amount = amount
        self.price = price
        self.status = status.lower()
        self.order_type = order_type.lower() if order_type else None
        self.filled = filled
        self.average_price = average_price
        self.exchange_id = exchange_id
        self.timestamp_ms = timestamp_ms
        self.error_message = error_message
        self.raw_data = raw_data or {}

    @classmethod
    def from_ccxt_response(cls, data: Dict[str, Any], exchange_id: str) -> Order:
        """CCXT'den gelen ham emir sözlüğünü standart bir `Order` nesnesine dönüştürür."""
        return cls(
            id=data.get('id'),
            symbol=data.get('symbol'),
            side=data.get('side'),
            amount=float(data.get('amount', 0.0)),
            price=float(data.get('price', 0.0)) if data.get('price') is not None else None,
            status=data.get('status', 'unknown'),
            order_type=data.get('type'),
            filled=float(data.get('filled', 0.0)),
            average_price=float(data.get('average', 0.0)) if data.get('average') is not None else None,
            exchange_id=exchange_id,
            timestamp_ms=int(data.get('timestamp', 0)),
            raw_data=data
        )

    def to_dict(self) -> Dict[str, Any]:
        """Emir nesnesini serileştirilebilir bir sözlüğe dönüştürür."""
        dt_object = None
        if self.timestamp_ms and self.timestamp_ms > 0:
            dt_object = datetime.fromtimestamp(self.timestamp_ms / 1000, tz=timezone.utc)

        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'amount': self.amount,
            'price': self.price,
            'status': self.status,
            'order_type': self.order_type,
            'filled': self.filled,
            'average_price': self.average_price,
            'exchange_id': self.exchange_id,
            'timestamp_ms': self.timestamp_ms,
            'datetime_utc': dt_object.isoformat() if dt_object else None,
            'error_message': self.error_message,
        }
    
    def __repr__(self) -> str:
        return (
            f"Order(id='{self.id}', exchange='{self.exchange_id}', symbol='{self.symbol}', "
            f"side='{self.side}', amount={self.amount}, status='{self.status}')"
        )