# exchange/models.py

"""
Borsa Etkileşimleri İçin Standart Veri Modelleri

Bu modül, farklı borsa API'lerinden gelen verileri standart ve tutarlı bir
yapıya dönüştürmek için kullanılan Pydantic veya dataclass tabanlı modelleri tanımlar.
Bu, sistemin geri kalanının borsa özelindeki veri yapılarından bağımsız olmasını sağlar.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Python 3.9 ve altı için: from __future__ import annotations

@dataclass
class Balance:
    """Tek bir varlık için bakiye bilgisini temsil eder."""
    asset: str  # Varlık adı (örn. "USDT")
    free: float  # Kullanılabilir bakiye
    used: float  # Kullanımda (emirlerde) olan bakiye
    total: float  # Toplam bakiye

@dataclass
class Ticker:
    """Bir işlem çifti için anlık piyasa verisini (ticker) temsil eder."""
    symbol: str  # CCXT formatında sembol (örn. "BTC/USDT")
    timestamp: int  # Verinin alındığı anın Unix milisaniye zaman damgası
    datetime: str  # Verinin alındığı anın ISO 8601 formatında string hali
    high: float  # Son 24 saatteki en yüksek fiyat
    low: float  # Son 24 saatteki en düşük fiyat
    last: float  # Son işlem fiyatı
    bid: float   # En iyi alış teklifi
    ask: float   # En iyi satış teklifi
    quote_volume: float  # Son 24 saatteki işlem hacmi (quote para birimi cinsinden, örn. USDT)

@dataclass
class Position:
    """Açık bir pozisyonun standartlaştırılmış halini temsil eder."""
    symbol: str  # CCXT formatında sembol (örn. "BTC/USDT")
    side: str  # 'long' veya 'short'
    contracts: float  # Pozisyon büyüklüğü (kontrat sayısı)
    entry_price: float  # Ortalama giriş fiyatı
    mark_price: float  # İşaret fiyatı
    leverage: int  # Kaldıraç
    unrealized_pnl: float  # Gerçekleşmemiş Kar/Zarar
    liquidation_price: Optional[float]  # Likidasyon fiyatı
    initial_margin: float  # Başlangıç marjini
    maintenance_margin: float # Sürdürme marjini
    margin_ratio: Optional[float] # Marjin oranı
    timestamp_ms: int  # Pozisyonun açıldığı veya son güncellendiği Unix milisaniye zaman damgası
    # --- Kopyalama ve Yönetim için Ek Alanlar ---
    original_symbol: str # Borsa API'sinden gelen ham sembol (örn. "BTCUSDT")

@dataclass
class Order:
    """Bir emrin standartlaştırılmış halini temsil eder."""
    id: str  # Borsa tarafından verilen emir ID'si
    symbol: str  # CCXT formatında sembol
    type: str  # 'market', 'limit', 'stop', vb.
    side: str  # 'buy' veya 'sell'
    amount: float  # İstenen miktar
    filled: float  # Gerçekleşen miktar
    price: Optional[float]  # Limit emirler için emir fiyatı
    average: Optional[float]  # Gerçekleşen ortalama fiyat
    status: str  # 'open', 'closed', 'canceled'
    timestamp_ms: int  # Emrin oluşturulduğu Unix milisaniye zaman damgası
    reduce_only: bool = False # Sadece azaltma emri mi?
    original_symbol: str = "" # Borsa API'sinden gelen ham sembol

@dataclass
class Trade:
    """Bir işlemin (trade) standartlaştırılmış halini temsil eder."""
    id: str
    order_id: str
    symbol: str
    type: str
    side: str
    price: float
    amount: float
    cost: float # İşlemin toplam maliyeti (price * amount)
    fee: Dict[str, Any] # {'cost': float, 'currency': str}
    timestamp_ms: int

@dataclass
class CommandResult:
    """handle_command tarafından döndürülen standart sonuç yapısı."""
    success: bool
    message: str
    order: Optional[Order] = None
    position: Optional[Position] = None
    data: Optional[Any] = None
    replication_summary: Optional[Dict[str, Any]] = None # Kopyalama özeti