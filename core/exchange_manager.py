# exchange/core/exchange_manager.py
import logging
from typing import Dict, Any, Optional

from ..interfaces.exchange_adapter_interface import ExchangeAdapterInterface
from ..adapters.binance_adapter import BinanceAdapter
# Gelecekte eklenecek diğer adaptörler buraya import edilecek
# from ..adapters.bybit_adapter import BybitAdapter

class ExchangeManager:
    """
    Borsa bağlantılarını (adaptörlerini) yöneten merkezi sınıf.

    Bu sınıf, bir 'bağlantı havuzu' (connection pool) görevi görerek,
    aynı API anahtarları için tekrar tekrar bağlantı oluşturulmasını engeller.
    Ayrıca, uygulama kapatılırken tüm bağlantıların güvenli bir şekilde
    sonlandırılmasını sağlar.
    """
    def __init__(self):
        # Desteklenen borsaları ve ilgili adaptör sınıflarını eşleştirir.
        self._adapter_map = {
            'binance': BinanceAdapter
            # 'bybit': BybitAdapter, # Gelecekte eklenebilir
        }
        # Aktif adaptör örneklerini saklar. Anahtar: f"{user_id}_{exchange_id}"
        self._active_adapters: Dict[str, ExchangeAdapterInterface] = {}
        # ### DÜZELTME: Liderin API bilgilerini saklamak için bir alan ###
        self._leader_api_info: Optional[Dict[str, Any]] = None

    def set_leader_api_info(self, leader_info: Dict[str, Any]):
        """
        ### YENİ METOT ###
        Liderin API bilgilerini ExchangeManager içinde ayarlar.
        Bu, __init__.py dosyasından çağrılacak.
        """
        required_keys = ['user_id', 'exchange_id', 'api_key', 'api_secret']
        if not all(key in leader_info and leader_info[key] for key in required_keys):
            logging.critical("ExchangeManager'a ayarlanan Lider API bilgileri eksik veya geçersiz!")
            self._leader_api_info = None
        else:
            self._leader_api_info = leader_info


    async def get_adapter(self, api_info: Dict[str, Any]) -> Optional[ExchangeAdapterInterface]:
        """
        Verilen API bilgileri için bir borsa adaptörü alır veya oluşturur.
        Eğer api_info 'leader' ise, saklanan lider bilgilerini kullanır.
        """
        if not isinstance(api_info, dict):
            logging.error(f"get_adapter'a geçersiz api_info tipi gönderildi: {type(api_info)}")
            return None

        # ### DÜZELTME: Lider istendiğinde, saklanan bilgileri kullan ###
        user_id_request = api_info.get("user_id")
        if user_id_request == "leader":
            if not self._leader_api_info:
                logging.critical("Lider adaptörü istendi ancak ExchangeManager'da lider API bilgisi ayarlanmamış!")
                return None
            # Lider için her zaman saklanan tam bilgiyi kullan
            api_info_to_use = self._leader_api_info
        else:
            # Diğer kullanıcılar için (kopyalama) gelen bilgiyi doğrula
            required_keys = ['user_id', 'exchange_id', 'api_key', 'api_secret']
            if not all(key in api_info and api_info[key] for key in required_keys):
                missing_keys = [key for key in required_keys if key not in api_info]
                logging.error(f"Takipçi API bilgisinde eksik anahtarlar var: {missing_keys}.")
                return None
            api_info_to_use = api_info
        
        user_id = api_info_to_use["user_id"]
        exchange_id = api_info_to_use["exchange_id"].lower()
        cache_key = f"{user_id}_{exchange_id}"

        if cache_key in self._active_adapters:
            return self._active_adapters[cache_key]

        logging.debug(f"Yeni adaptör oluşturuluyor: {cache_key}")
        AdapterClass = self._adapter_map.get(exchange_id)

        if not AdapterClass:
            logging.error(f"Desteklenmeyen borsa: '{exchange_id}'.")
            return None

        adapter = AdapterClass(api_info_to_use) # Tam bilgiyi adaptöre ver

        try:
            await adapter.connect()
            self._active_adapters[cache_key] = adapter
            logging.debug(f"Yeni adaptör başarıyla oluşturuldu ve bağlandı: {cache_key}")
            return adapter
        except Exception as e:
            logging.critical(f"Adaptör ({cache_key}) bağlanırken kritik hata: {e}")
            await adapter.close()
            return None

    async def close_all_adapters(self) -> None:
        """Tüm aktif borsa bağlantılarını güvenli bir şekilde kapatır."""
        logging.info(f"{len(self._active_adapters)} aktif adaptör kapatılıyor...")
        for cache_key, adapter in list(self._active_adapters.items()):
            try:
                await adapter.close()
            except Exception as e:
                logging.error(f"Adaptör ({cache_key}) kapatılırken hata: {e}")
        self._active_adapters.clear()
        logging.info("Tüm adaptörler kapatıldı ve havuz temizlendi.")