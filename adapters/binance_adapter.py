# exchange/adapters/binance_adapter.py
import logging
from typing import List, Dict, Any, Optional

import ccxt.async_support as ccxt

from ..interfaces.exchange_adapter_interface import ExchangeAdapterInterface
from ..models import Position, Order
from ..utils import format_symbol_for_ccxt

class BinanceAdapter(ExchangeAdapterInterface):
    """
    Binance borsası için tam donanımlı, özel adaptör.
    Bu sınıf, emir/pozisyon yönetimi, bakiye işlemleri ve tüm standart veri
    çekme işlemleri için birleşik bir arayüz sağlar.
    """
    def __init__(self, api_info: Dict[str, Any]):
        super().__init__(api_info)
        self.exchange_id = 'binance'

    async def connect(self) -> None:
        """Binance borsasına bağlanır ve marketleri yükler."""
        if self.exchange:
            return
        if not self.api_info or 'api_key' not in self.api_info or 'api_secret' not in self.api_info:
            raise ValueError("BinanceAdapter: Bağlantı için 'api_key' ve 'api_secret' gereklidir.")
        
        logging.debug(f"Binance'e ({self.api_info.get('user_id', 'N/A')}) bağlanılıyor...")
        try:
            self.exchange = ccxt.binance({
                'apiKey': self.api_info['api_key'],
                'secret': self.api_info['api_secret'],
                'enableRateLimit': True,
                'options': {'defaultType': 'future', 'adjustForTimeDifference': True, 'warnOnFetchOpenOrdersWithoutSymbol': False},
            })
            await self.load_markets(force_reload=True)
            logging.debug(f"✅ Binance borsasına ({self.api_info.get('user_id', 'N/A')}) başarıyla bağlanıldı.")
        except ccxt.AuthenticationError as e:
            logging.critical(f"Binance kimlik doğrulama hatası: {e}")
            raise ConnectionError(f"Binance kimlik doğrulama hatası: {e}") from e
        except Exception as e:
            logging.critical(f"Binance bağlantısı kurulurken hata: {e}")
            raise ConnectionError(f"Binance bağlantı hatası: {e}") from e

    async def close(self) -> None:
        """Binance bağlantısını kapatır."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None
            logging.debug(f"Binance bağlantısı ({self.api_info.get('user_id', 'N/A')}) kapatıldı.")

    # --- Standart Arayüz Metotları (Emir, Pozisyon, Kaldıraç) ---

    async def get_positions(self, symbols: Optional[List[str]] = None) -> List[Position]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        try:
            raw_positions = await self.exchange.fetch_positions(symbols)
            return [
                pos for data in raw_positions
                if abs(float(data.get('info', {}).get('positionAmt', '0'))) > 1e-9
                and (pos := Position.from_ccxt_response(data, self.exchange_id)) is not None
            ]
        except Exception as e:
            logging.error(f"Binance pozisyonları alınırken hata: {e}", exc_info=False)
            return []

    async def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: Optional[float] = None, stop_price: Optional[float] = None, params: Optional[Dict[str, Any]] = None) -> Order:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        symbol_ccxt = format_symbol_for_ccxt(symbol)
        final_params = params or {}

        # Post-only order type'ı özel olarak işle
        if order_type.lower() == 'post_only':
            order_type = 'limit'  # Post-only aslında limit order'dır
            final_params['postOnly'] = True
            if not price:
                raise ValueError("Post-only emirler için fiyat belirtilmelidir")
            logging.debug(f"Post-only emir hazırlanıyor: {symbol_ccxt} {side} {amount} @ {price}")
        
        # Post-only parametresi manuel olarak gönderilmişse de ekle
        if final_params.get('post_only', False):
            final_params['postOnly'] = True
            final_params.pop('post_only', None)  # CCXT'nin anlamadığı parametreyi temizle
            logging.debug(f"Post-only parametresi eklendi: {symbol_ccxt} {side} {amount}")
        
        # Post-only emirlerde fiyat doğrulaması
        if final_params.get('postOnly', False) and not price:
            raise ValueError(f"Post-only emir için fiyat belirtilmelidir: {symbol_ccxt}")

        if order_type.lower() == 'stop_limit' and stop_price:
            final_params['stopPrice'] = stop_price

        if 'takeProfitPrice' in final_params:
            final_params['takeProfit'] = {'type': 'TAKE_PROFIT_MARKET', 'price': final_params.pop('takeProfitPrice')}
        if 'stopLossPrice' in final_params:
            final_params['stopLoss'] = {'type': 'STOP_MARKET', 'price': final_params.pop('stopLossPrice')}

        try:
            raw_order = await self.exchange.create_order(symbol_ccxt, order_type, side, amount, price, final_params)
            return Order.from_ccxt_response(raw_order, self.exchange_id)
        except Exception as e:
            logging.error(f"Binance'e emir gönderilirken hata: {e}", exc_info=False)
            return Order(id=None, symbol=symbol_ccxt, side=side, amount=amount, price=price, status='failed', error_message=str(e), exchange_id=self.exchange_id)

    # <<< DEĞİŞİKLİK BURADA: set_leverage metodu güncellendi ve sadeleştirildi >>>
    async def set_leverage(self, symbol: str, leverage: int, margin_mode: str = 'isolated') -> bool:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        symbol_ccxt = format_symbol_for_ccxt(symbol)
        try:
            # CCXT'nin set_leverage metodu, 'params' argümanı aracılığıyla
            # borsaya özel ek parametreler gönderebilir. Binance için marjin tipini
            # bu şekilde göndereceğiz. Bu, hem daha temiz hem de CCXT standartlarına uygun bir yoldur.
            await self.exchange.set_leverage(
                abs(int(leverage)), 
                symbol_ccxt, 
                {'marginMode': margin_mode} # 'marginMode' parametresini kullanarak marjin tipini belirt
            )
            logging.debug(f"LEVERAGE-SET: {symbol_ccxt} için kaldıraç {leverage}x ve marjin modu '{margin_mode}' olarak ayarlandı.")
            return True
        except ccxt.ExchangeError as e:
            # HATA DÜZELTMESİ: .code özelliğine erişmeden önce var olup olmadığını kontrol et.
            # Bu, 'BadRequest' gibi .code özelliği olmayan hataların AttributeError fırlatmasını önler.
            if hasattr(e, 'code') and e.code == -4046 and "No need to change margin type" in str(e):
                # Bu özel hata kodu (-4046), marjin modunun zaten istenen modda olduğu
                # ve değiştirilmesine gerek olmadığı anlamına gelir. Bu bir hata değildir.
                logging.debug(f"{symbol_ccxt}: Marjin modu zaten '{margin_mode}', sadece kaldıraç ayarlanıyor...")
                
                # Marjin tipi hatasını yoksayarak SADECE kaldıracı tekrar ayarlamayı dene.
                try:
                    await self.exchange.set_leverage(abs(int(leverage)), symbol_ccxt)
                    logging.debug(f"LEVERAGE-SET: {symbol_ccxt} için kaldıraç {leverage}x olarak ayarlandı (marjin modu değişmedi).")
                    return True
                except Exception as inner_e:
                    # Sadece kaldıraç ayarlama işlemi de başarısız olursa bunu logla.
                    logging.error(f"Marjin modu hatası sonrası kaldıraç ayarlanamadı ({symbol_ccxt}): {inner_e}", exc_info=False)
                    return False
            else:
                # Diğer tüm borsa hatalarını (örn. BadRequest, InvalidOrder) burada yakala ve logla.
                logging.error(f"Kaldıraç ayarlanamadı ({symbol_ccxt}): {e}", exc_info=False)
                return False
        except Exception as e:
            # CCXT dışı genel hatalar
            logging.error(f"Kaldıraç ayarlanırken beklenmedik hata ({symbol_ccxt}): {e}", exc_info=False)
            return False

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.cancel_order(order_id, format_symbol_for_ccxt(symbol))

    # --- GENİŞLETİLMİŞ VERİ ÇEKME METOTLARI (WRAPPER'LAR) ---

    async def load_markets(self, force_reload: bool = False) -> Dict:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.load_markets(force_reload)

    async def fetch_balance(self, params: Dict = {}) -> Dict:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        if 'type' not in params:
            params['type'] = 'future'
        return await self.exchange.fetch_balance(params)

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = None, params: Dict = {}) -> List[list]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit, params)

    async def fetch_ticker(self, symbol: str, params: Dict = {}) -> Dict:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_ticker(symbol, params)

    async def fetch_tickers(self, symbols: Optional[List[str]] = None, params: Dict = {}) -> Dict:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_tickers(symbols, params)
        
    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_order(order_id, symbol)

    async def fetch_open_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None, params: Dict = {}) -> List[Dict]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_open_orders(symbol, since, limit, params)

    async def fetch_closed_orders(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None, params: Dict = {}) -> List[Dict]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_closed_orders(symbol, since, limit, params)

    async def fetch_my_trades(self, symbol: Optional[str] = None, since: Optional[int] = None, limit: Optional[int] = None, params: Dict = {}) -> List[Dict]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.exchange.fetch_my_trades(symbol, since, limit, params)

    def market(self, symbol: str) -> Optional[Dict]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return self.exchange.market(format_symbol_for_ccxt(symbol))

    # --- Standart Arayüz Metotları (Değer Hesaplama ve Normalizasyon) ---

    async def get_total_account_value_usdt(self) -> Optional[float]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        try:
            balance = await self.fetch_balance()
            return float(balance.get('info', {}).get('totalWalletBalance', 0.0))
        except Exception as e:
            logging.error(f"Binance toplam hesap değeri alınırken hata: {e}", exc_info=False)
            return None
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return await self.fetch_ticker(format_symbol_for_ccxt(symbol))

    async def normalize_amount(self, symbol: str, amount: float) -> float:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        return float(self.exchange.amount_to_precision(format_symbol_for_ccxt(symbol), amount))

    async def get_market_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.exchange: raise ConnectionError("Borsa bağlantısı kapalı.")
        market_data = self.market(symbol)
        return market_data.get('limits') if market_data else None