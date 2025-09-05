# exchange/services/command_executor.py
import logging
from typing import Dict, Any, List, Optional

from ..core.exchange_manager import ExchangeManager
from ..services.replication_service import ReplicationService
from ..models.order import Order
from ..utils.helpers import format_symbol_for_ccxt
from ..utils.calculator import adjust_amount_for_limits

class CommandExecutor:
    """
    Lider hesap üzerinde tüm alım/satım ve pozisyon yönetimi komutlarını
    yürüten merkezi servis. Başarılı işlemler anında kopyalama için
    ReplicationService'e iletilir.
    """

    def __init__(self, manager: ExchangeManager, replication_service: ReplicationService):
        self.manager = manager
        self.replication = replication_service
        self.leader_api_info = {"user_id": "leader", "exchange_id": "binance"} # Varsayılan lider
        logging.debug("CommandExecutor başlatıldı.")

    async def execute(self, command: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Gelen bir komutu işler ve uygun lider eylemini tetikler.

        Args:
            command (Dict[str, Any]): İşlenecek komut sözlüğü.
                                     Örn: {'action': 'buy', 'symbol': 'BTC/USDT', ...}

        Returns:
            List[Dict[str, Any]]: İşlem sonucunu içeren bir liste.
        """
        action = command.get("action", "").lower()
        log_prefix = f"EXECUTE ({action.upper()})"
        logging.info(f"{log_prefix}: Komut alındı: {command}")

        leader_adapter = await self.manager.get_adapter(self.leader_api_info)
        if not leader_adapter:
            msg = "Lider adaptörü alınamadığı için komut işlenemiyor."
            logging.critical(f"{log_prefix}: {msg}")
            return [{"status": "failed", "message": msg}]

        handler_map = {
            "buy": self._handle_open_position,
            "sell": self._handle_open_position,
            "close_position": self._handle_close_position,
            "scale_out": self._handle_scale_out,
            "scale_in": self._handle_scale_in,
            "set_leverage": self._handle_set_leverage,
            "cancel": self._handle_cancel_order,
        }

        handler = handler_map.get(action)
        if not handler:
            msg = f"Desteklenmeyen komut: '{action}'"
            logging.error(f"{log_prefix}: {msg}")
            return [{"status": "failed", "message": msg}]

        try:
            # ### YENİ: Kopyalama için orijinal komut detaylarını emre ekle ###
            # Bu, ReplicationService'in liderin asıl niyetini (örn. kaldıraç) bilmesini sağlar.
            params = command.get('params', {})
            # Sadece pozisyon açma/artırma emirleri için bu detayı eklemek mantıklıdır.
            if action in ["buy", "sell"]:
                params['command_details'] = {
                    'action': command.get('action'),
                    'leverage': command.get('leverage'),
                    'amount': command.get('amount')
                }
            command['params'] = params
            
            result_order = await handler(leader_adapter, command)
            
            if isinstance(result_order, Order):
                if result_order.status != 'failed':
                    # Sadece 'market' emirleri anında kopyalanır. Limit emirler dolduğunda
                    # kopyalanmalıdır, bu daha gelişmiş bir webhook/websocket yapısı gerektirir.
                    if result_order.order_type == 'market':
                        logging.info(f"{log_prefix}: Lider piyasa emri başarılı. Kopyalama tetikleniyor...")
                        replication_summary = await self.replication.replicate_action(
                            leader_api_info=self.leader_api_info,
                            leader_order=result_order
                        )
                        return [{
                            "status": "success",
                            "leader_order": result_order.to_dict(),
                            "replication": replication_summary
                        }]
                    else:
                        logging.info(f"{log_prefix}: Lider limit/stop emri ({result_order.order_type}) borsaya iletildi. Kopyalama anında tetiklenmedi.")
                        return [{"status": "success", "leader_order": result_order.to_dict(), "replication": "Limit order, not replicated immediately."}]
                else:
                    logging.error(f"{log_prefix}: Lider işlemi BAŞARISIZ. Detaylar: {result_order.error_message}")
                    return [{"status": "failed", "details": result_order.to_dict()}]
            
            # set_leverage, cancel_order gibi emir oluşturmayan işlemler için
            elif result_order is None or isinstance(result_order, (bool, dict)):
                 logging.info(f"{log_prefix}: Komut bir emir oluşturmadı veya kopyalanabilir değil. İşlem tamamlandı.")
                 return [{"status": "success", "message": "Emir oluşturmayan işlem tamamlandı.", "details": result_order}]
            
            else:
                 return [{"status": "failed", "message": f"Bilinmeyen bir sonuç tipi döndü: {type(result_order)}"}]

        except Exception as e:
            logging.critical(f"{log_prefix}: Komut işlenirken beklenmedik hata: {e}", exc_info=True)
            return [{"status": "failed", "message": f"Genel Hata: {e}"}]

    async def _handle_open_position(self, adapter, command: Dict[str, Any]) -> Optional[Order]:
        """Yeni bir pozisyon açar (buy/sell). Emri borsaya göndermeden önce miktar ve kaldıraç ayarlarını yapar."""
        symbol = command['symbol']
        original_amount = float(command['amount'])
        leverage = int(command['leverage'])
        margin_mode = command.get('margin_mode', 'isolated')
        
        # ### DÜZELTME ### Kopyalama için orijinal komutu içeren `params`'ı al
        params = command.get('params', {})
        
        # Post-only parametresini ekle
        if command.get('post_only', False):
            params['post_only'] = True
        elif command.get('order_type') == 'post_only':
            params['post_only'] = True

        # ### DÜZELTME: Emir göndermeden ÖNCE kaldıraç ayarla ###
        logging.debug(f"Pozisyon açmadan önce liderin kaldıracı ayarlanıyor: {symbol}, {leverage}x, {margin_mode}")
        leverage_set_success = await adapter.set_leverage(symbol, leverage, margin_mode)
        if not leverage_set_success:
            msg = f"Lider için {symbol} işlemi: Kaldıraç ({leverage}x) ayarlanamadı. İşlem iptal edildi."
            logging.error(msg)
            return Order(id=None, symbol=symbol, side=command['action'], amount=original_amount, status='failed', error_message=msg, exchange_id=adapter.exchange_id)

        final_amount = await adjust_amount_for_limits(adapter, symbol, original_amount)

        if final_amount is None:
            msg = f"Lider için {symbol} işlemi: Miktar ({original_amount}) borsa limitlerine ayarlanamadı. İşlem iptal edildi."
            logging.error(msg)
            return Order(id=None, symbol=symbol, side=command['action'], amount=original_amount, status='failed', error_message=msg, exchange_id=adapter.exchange_id)

        if abs(final_amount - original_amount) > 1e-9: # Floating point karşılaştırması için
            logging.warning(f"Lider için {symbol} işlemi: Komut miktarı ({original_amount}) borsa limitleri için ({final_amount}) olarak ayarlandı.")

        return await adapter.place_order(
            symbol=symbol,
            order_type=command.get('order_type', 'market'),
            side=command['action'],
            amount=final_amount,
            price=command.get('price'),
            params=params # Komut detaylarını içeren params'ı adaptöre ilet
        )

    async def _handle_close_position(self, adapter, command: Dict[str, Any]) -> Optional[Order]:
        """
        Mevcut bir pozisyonu tamamen kapatır. Her zaman 'reduceOnly' parametresi ekler.
        """
        symbol_ccxt = format_symbol_for_ccxt(command['symbol'])
        positions = await adapter.get_positions([symbol_ccxt]) # Sadece ilgili sembolü sorgula
        target_pos = next((p for p in positions if p.symbol == symbol_ccxt), None)

        if not target_pos:
            msg = f"Kapatılacak pozisyon bulunamadı: {symbol_ccxt}"
            logging.warning(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=0, status="failed", error_message=msg, exchange_id=adapter.exchange_id)
        
        logging.info(f"{symbol_ccxt} pozisyonu market emri ile kapatılıyor.")

        return await adapter.place_order(
            symbol=symbol_ccxt,
            order_type='market',
            side='sell' if target_pos.side == 'long' else 'buy',
            amount=target_pos.contracts,
            params={'reduceOnly': True} # Kapatma işlemlerinde her zaman reduceOnly kullan
        )
        
    async def _handle_scale_out(self, adapter, command: Dict[str, Any]) -> Optional[Order]:
        """Mevcut bir pozisyonu kısmen kapatır."""
        symbol_ccxt = format_symbol_for_ccxt(command['symbol'])
        positions = await adapter.get_positions([symbol_ccxt])
        target_pos = next((p for p in positions if p.symbol == symbol_ccxt), None)

        if not target_pos:
            msg = f"Ölçeklenecek pozisyon bulunamadı: {symbol_ccxt}"
            logging.warning(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=0, status="failed", error_message=msg, exchange_id=adapter.exchange_id)

        original_amount_to_close = 0.0
        if 'amount' in command:
            original_amount_to_close = float(command['amount'])
        elif 'percentage' in command:
            original_amount_to_close = target_pos.contracts * (float(command['percentage']) / 100.0)
        
        if original_amount_to_close <= 0:
            msg = f"Geçersiz scale-out miktarı: {original_amount_to_close}"
            logging.error(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=0, status="failed", error_message=msg, exchange_id=adapter.exchange_id)

        final_amount_to_close = await adjust_amount_for_limits(adapter, symbol_ccxt, original_amount_to_close)

        if final_amount_to_close is None or final_amount_to_close > target_pos.contracts:
            msg = f"Lider için {symbol_ccxt} scale-out miktarı ayarlanamadı veya mevcut pozisyondan büyük. İşlem iptal edildi."
            logging.error(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=original_amount_to_close, status='failed', error_message=msg, exchange_id=adapter.exchange_id)

        # Parametreleri hazırla
        params = command.get('params', {})
        
        # Post-only parametresini ekle
        if command.get('post_only', False):
            params['post_only'] = True
        elif command.get('order_type') == 'post_only':
            params['post_only'] = True

        return await adapter.place_order(
            symbol=symbol_ccxt,
            order_type=command.get('order_type', 'market'),
            side='sell' if target_pos.side == 'long' else 'buy',
            amount=final_amount_to_close,
            price=command.get('price'),
            params={**params, 'reduceOnly': True}  # reduceOnly her zaman ekle
        )

    async def _handle_scale_in(self, adapter, command: Dict[str, Any]) -> Optional[Order]:
        """Mevcut bir pozisyona ekleme yapar (scale-in)."""
        symbol = command['symbol']
        symbol_ccxt = format_symbol_for_ccxt(symbol)
        
        # Mevcut pozisyonu kontrol et
        positions = await adapter.get_positions([symbol_ccxt])
        target_pos = next((p for p in positions if p.symbol == symbol_ccxt), None)
        
        if not target_pos:
            msg = f"Scale-in için pozisyon bulunamadı: {symbol_ccxt}"
            logging.warning(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=0, status="failed", error_message=msg, exchange_id=adapter.exchange_id)
        
        # Scale-in miktarını al
        original_amount = float(command['amount'])
        
        if original_amount <= 0:
            msg = f"Geçersiz scale-in miktarı: {original_amount}"
            logging.error(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=original_amount, status="failed", error_message=msg, exchange_id=adapter.exchange_id)
        
        # Miktar limitlerini kontrol et
        final_amount = await adjust_amount_for_limits(adapter, symbol_ccxt, original_amount)
        
        if final_amount is None:
            msg = f"Scale-in miktarı borsa limitlerine uygun değil: {original_amount}"
            logging.error(msg)
            return Order(id=None, symbol=symbol_ccxt, side="unknown", amount=original_amount, status="failed", error_message=msg, exchange_id=adapter.exchange_id)
        
        if abs(final_amount - original_amount) > 1e-9:
            logging.warning(f"Scale-in miktarı borsa limitleri için ayarlandı: {original_amount} -> {final_amount}")
        
        # Pozisyon yönüne göre buy/sell belirle (action alanından al)
        side = command['action']  # 'buy' veya 'sell' prompt'tan gelir
        
        # Güvenlik kontrolü: side pozisyon yönü ile uyumlu mu?
        if (target_pos.side == 'long' and side != 'buy') or (target_pos.side == 'short' and side != 'sell'):
            msg = f"Scale-in yön hatası: {target_pos.side} pozisyon için {side} komutu uygun değil"
            logging.error(msg)
            return Order(id=None, symbol=symbol_ccxt, side=side, amount=original_amount, status="failed", error_message=msg, exchange_id=adapter.exchange_id)
        
        # Parametreleri hazırla
        params = command.get('params', {})
        
        # Post-only parametresini ekle
        if command.get('post_only', False):
            params['post_only'] = True
        elif command.get('order_type') == 'post_only':
            params['post_only'] = True
        
        logging.info(f"{symbol_ccxt} pozisyonuna scale-in yapılıyor: {side} {final_amount}")
        
        return await adapter.place_order(
            symbol=symbol_ccxt,
            order_type=command.get('order_type', 'market'),
            side=side,
            amount=final_amount,
            price=command.get('price'),
            params={**params, 'reduceOnly': False}  # Scale-in pozisyonu büyütür
        )

    async def _handle_set_leverage(self, adapter, command: Dict[str, Any]) -> bool:
        """Kaldıracı ayarlar. Bu bir emir oluşturmadığı için kopyalanmaz."""
        success = await adapter.set_leverage(
            symbol=command['symbol'],
            leverage=int(command['leverage']),
            margin_mode=command.get('margin_mode', 'isolated')
        )
        logging.info(f"Kaldıraç ayarlama sonucu ({command['symbol']}): {'Başarılı' if success else 'Başarısız'}")
        return success # Emir objesi yerine bool döndürür

    async def _handle_cancel_order(self, adapter, command: Dict[str, Any]) -> Dict[str, Any]:
        """Açık bir emri iptal eder. Bu bir emir oluşturmadığı için kopyalanmaz."""
        order_id = command.get('order_id')
        symbol = command.get('symbol')
        if not order_id or not symbol:
            msg = "Emir iptali için 'order_id' ve 'symbol' gereklidir."
            logging.error(msg)
            return {"status": "failed", "message": msg}
        
        result = await adapter.cancel_order(order_id, symbol)
        logging.info(f"Emir iptal sonucu ({order_id}): {result.get('status', 'Bilinmiyor')}")
        return result