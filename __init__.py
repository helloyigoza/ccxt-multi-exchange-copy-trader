# exchange/__init__.py

"""
Bu paket, borsa etkileşimleri için gerekli olan tüm OOP bileşenlerini içerir.
Bu __init__ dosyası, sadece bu bileşenleri dış dünyaya kolayca erişilebilir kılar.
Uygulama başlatma mantığı burada yer almaz.
"""

import logging

# Gerekli Sınıflar ve Modeller
from .core.exchange_manager import ExchangeManager
from .services.command_executor import CommandExecutor
from .services.replication_service import ReplicationService
from .services.sync_service import SyncService
from .models import Position as StandardPosition, Order as StandardOrder
from .interfaces.exchange_adapter_interface import ExchangeAdapterInterface
from .utils import format_symbol_for_ccxt, load_api_keys_from_file

# Bu __all__ listesi, 'from exchange import *' kullanıldığında nelerin import edileceğini tanımlar.
__all__ = [
    # Çekirdek
    "ExchangeManager",
    
    # Servisler
    "CommandExecutor",
    "ReplicationService",
    "SyncService",
    
    # Veri Modelleri
    "StandardPosition",
    "StandardOrder",
    
    # Arayüz
    "ExchangeAdapterInterface",
    
    # Yardımcı Fonksiyonlar
    "format_symbol_for_ccxt",
    "load_api_keys_from_file",
]

logging.debug("Exchange paketi (OOP bileşenleri) yüklendi.")