# exchange/interfaces/exchange_adapter_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

import ccxt.async_support as ccxt
from ..models.position import Position
from ..models.order import Order

class ExchangeAdapterInterface(ABC):
    """
    Tüm borsa adaptörleri için bir arayüz tanımlar.

    Bu soyut sınıf, farklı borsalarla (Binance, Bybit, vb.) etkileşim kurmak için
    gerekli olan tüm temel fonksiyonların bir "sözleşmesini" oluşturur.
    Her yeni borsa entegrasyonu, bu arayüzü uygulayan bir adaptör sınıfı
    oluşturarak sisteme kolayca dahil edilebilir.
    """

    def __init__(self, api_info: Dict[str, Any]):
        """
        Adaptör başlatıcı.

        Args:
            api_info (Dict[str, Any]): 'api_key', 'api_secret' ve gerekirse
                                       'api_passphrase' gibi bilgileri içeren sözlük.
        """
        self.exchange: Optional[ccxt.Exchange] = None
        self.api_info = api_info
        self.exchange_id = api_info.get("exchange_id", "unknown")

    @abstractmethod
    async def connect(self) -> None:
        """
        Borsaya asenkron olarak bağlanır ve `self.exchange` nesnesini başlatır.
        Bağlantı başarısız olursa istisna (exception) fırlatmalıdır.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Borsa bağlantısını güvenli bir şekilde kapatır.
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Hesaptaki tüm açık pozisyonları alır ve standartlaştırılmış `Position`
        nesnelerinden oluşan bir liste olarak döndürür.

        Returns:
            List[Position]: Açık pozisyonların listesi.
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Order:
        """
        Borsaya bir emir gönderir.

        Args:
            symbol (str): İşlem çifti (örn. 'BTC/USDT').
            order_type (str): Emir tipi ('market', 'limit', vb.).
            side (str): Emir yönü ('buy' veya 'sell').
            amount (float): Emir miktarı.
            price (Optional[float]): Limit emirler için fiyat.
            params (Optional[Dict[str, Any]]): Borsaya özel ek parametreler
                                              (örn. {'reduceOnly': True}).

        Returns:
            Order: Oluşturulan emrin standartlaştırılmış `Order` nesnesi.
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Belirtilen ID'ye sahip bir emri iptal eder.

        Args:
            order_id (str): İptal edilecek emrin ID'si.
            symbol (str): Emrin ait olduğu işlem çifti.

        Returns:
            Dict[str, Any]: Borsa tarafından döndürülen iptal sonucu.
        """
        pass

    @abstractmethod
    async def set_leverage(
        self,
        symbol: str,
        leverage: int,
        margin_mode: str = 'isolated'
    ) -> bool:
        """
        Belirtilen sembol için kaldıracı ve marjin modunu ayarlar.

        Args:
            symbol (str): İşlem çifti.
            leverage (int): Ayarlanacak kaldıraç değeri.
            margin_mode (str): 'isolated' veya 'cross'.

        Returns:
            bool: İşlemin başarılı olup olmadığını belirten boolean değer.
        """
        pass

    @abstractmethod
    async def get_total_account_value_usdt(self) -> Optional[float]:
        """
        Hesabın toplam değerini (serbest bakiye + pozisyon marjları)
        USDT cinsinden hesaplar.

        Returns:
            Optional[float]: Hesabın toplam USDT değeri veya hata durumunda None.
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Belirtilen sembol için son fiyat ve diğer ticker bilgilerini alır.

        Returns:
            Dict[str, Any]: Ticker bilgileri.
        """
        pass

    @abstractmethod
    async def normalize_amount(self, symbol: str, amount: float) -> float:
        """
        Verilen miktarı, borsanın o sembol için belirlediği hassasiyet ve
        adım limitlerine göre normalleştirir.

        Args:
            symbol (str): İşlem çifti.
            amount (float): Normalleştirilecek miktar.

        Returns:
            float: Normalleştirilmiş miktar.
        """
        pass

    @abstractmethod
    async def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Bir sembol için minimum miktar, minimum maliyet gibi piyasa limitlerini alır.

        Returns:
            Optional[Dict[str, Any]]: Limitleri içeren bir sözlük veya None.
        """
        pass