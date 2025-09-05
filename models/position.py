# exchange/models/position.py
from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class Position:
    """
    Tüm borsalar için standartlaştırılmış bir pozisyon veri modeli.
    """
    def __init__(
        self,
        symbol: str,
        side: str,
        contracts: float,
        entry_price: float,
        mark_price: float,
        leverage: int,
        unrealized_pnl: float,
        liquidation_price: Optional[float] = None,
        exchange_id: Optional[str] = None,
        timestamp_ms: Optional[int] = None,
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.symbol = symbol
        self.side = side.lower()
        self.contracts = contracts
        self.entry_price = entry_price
        self.mark_price = mark_price
        self.leverage = leverage
        self.unrealized_pnl = unrealized_pnl
        self.liquidation_price = liquidation_price
        self.exchange_id = exchange_id
        self.timestamp_ms = timestamp_ms
        self.raw_data = raw_data or {} # Hata ayıklama için ham veriyi sakla

    @classmethod
    def from_ccxt_response(cls, data: Dict[str, Any], exchange_id: str) -> Optional[Position]:
        """
        CCXT'den gelen ham pozisyon sözlüğünü standart bir `Position` nesnesine dönüştürür.
        
        Bu fabrika metodu, farklı borsaların döndürdüğü çeşitli anahtar isimlerini
        ve veri formatlarını tanıyarak tutarlılık sağlar.
        """
        try:
            info = data.get('info', {})

            # Pozisyon büyüklüğünü al (farklı anahtarları dene)
            contracts_str = info.get('positionAmt', data.get('contracts', '0'))
            contracts = float(contracts_str)
            
            # --- DEĞİŞİKLİK: Sembolü al ve temizle (örn: 'MEMEFI/USDT:USDT' -> 'MEMEFI/USDT') ---
            symbol_raw = data.get('symbol', 'N/A')
            symbol = symbol_raw.split(':')[0] if isinstance(symbol_raw, str) else 'N/A'
            # --- DEĞİŞİKLİK SONU ---

            # Tarafı belirle (eğer 'side' yoksa kontrat miktarına göre karar ver)
            side = data.get('side', 'long' if contracts > 0 else 'short').lower()

            # Kaldıraç değerini güvenli bir şekilde al
            leverage_int = abs(int((contracts * data.get('entryPrice', info.get('entryPrice', 1))) / den) if (den := data.get('initialMargin', info.get('initialMargin', 1.0))) != 0 else 1)

            # Likidasyon fiyatını güvenli bir şekilde al
            liquidation_val = data.get('liquidationPrice', info.get('liquidationPrice'))
            liquidation_price_float = None # Varsayılan None
            if liquidation_val is not None and str(liquidation_val) != '0': # '0' ise None olarak kabul et
                try:
                    liquidation_price_float = float(liquidation_val)
                except (ValueError, TypeError):
                    logging.warning(f"Geçersiz likidasyon fiyatı değeri '{liquidation_val}'. Varsayılan None kullanılıyor.")
                    liquidation_price_float = None
            return cls(
                symbol=symbol, # Temizlenmiş sembolü kullan
                side=side,
                contracts=abs(contracts), # Her zaman pozitif değer
                entry_price=float(data.get('entryPrice', info.get('entryPrice', 0.0))),
                mark_price=float(data.get('markPrice', info.get('markPrice', 0.0))),
                leverage=leverage_int,
                unrealized_pnl=float(data.get('unrealizedPnl', info.get('unrealisedPnl', 0.0))),
                liquidation_price=liquidation_price_float,
                exchange_id=exchange_id,
                timestamp_ms=int(data.get('timestamp', 0)),
                raw_data=data
            )
        except (ValueError, TypeError, KeyError) as e:
            logging.error(f"CCXT pozisyon verisi standart modele dönüştürülürken hata: {e}. Veri: {data}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Pozisyon nesnesini serileştirilebilir bir sözlüğe dönüştürür."""
        dt_object = None
        if self.timestamp_ms and self.timestamp_ms > 0:
            dt_object = datetime.fromtimestamp(self.timestamp_ms / 1000, tz=timezone.utc)
        
        return {
            'symbol': self.symbol,
            'side': self.side,
            'contracts': self.contracts,
            'entry_price': self.entry_price,
            'mark_price': self.mark_price,
            'leverage': self.leverage,
            'unrealized_pnl': self.unrealized_pnl,
            'liquidation_price': self.liquidation_price,
            'exchange_id': self.exchange_id,
            'timestamp_ms': self.timestamp_ms,
            'datetime_utc': dt_object.isoformat() if dt_object else None
        }

    def __repr__(self) -> str:
        return (
            f"Position(exchange='{self.exchange_id}', symbol='{self.symbol}', side='{self.side}', "
            f"contracts={self.contracts}, entry_price={self.entry_price})"
        )