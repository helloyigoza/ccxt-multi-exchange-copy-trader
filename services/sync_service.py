# exchange/services/sync_service.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from ..core.exchange_manager import ExchangeManager
from ..interfaces.exchange_adapter_interface import ExchangeAdapterInterface
from ..models.position import Position
from ..utils.helpers import load_api_keys_from_file, format_symbol_for_ccxt # format_symbol_for_ccxt import edildi
from ..utils.calculator import calculate_follower_amount

# Yapılandırılabilir Sabitler
SYNC_INTERVAL_SECONDS = 20 # Senkronizasyon aralığı düşürüldü
LATE_JOIN_MAX_PRICE_CHANGE_PERCENT = 0.75 # Fiyat %0.75'den fazla değişmişse geç katılım yapma
LATE_JOIN_MAX_AGE_MINUTES = 30 # 30 dakikadan eski pozisyonlara geç katılım yapma

class SyncService:
    """
    Lider ve takipçi hesapları arasında periyodik senkronizasyon sağlar.
    - Yetim pozisyonları kapatır.
    - Eksik pozisyonları açar (geç katılım).
    - Miktar tutarsızlıklarını düzeltir (gelecekte eklenebilir).
    """
    def __init__(self, manager: ExchangeManager):
        self.manager = manager
        self._task: Optional[asyncio.Task] = None
        self._is_running = False
        self.leader_api_info = {"user_id": "leader", "exchange_id": "binance"}

    async def start(self):
        """Senkronizasyon döngüsünü başlatır."""
        if self._is_running:
            logging.warning("SyncService zaten çalışıyor.")
            return
        self._is_running = True
        self._task = asyncio.create_task(self._sync_loop())
        logging.debug(f"SyncService başlatıldı. Döngü aralığı: {SYNC_INTERVAL_SECONDS} saniye.")

    async def stop(self):
        """Senkronizasyon döngüsünü durdurur."""
        if not self._is_running or not self._task:
            logging.warning("SyncService zaten durdurulmuş.")
            return
        self._is_running = False
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        logging.debug("SyncService durduruldu.")

    async def _sync_loop(self):
        """Senkronizasyon işlemlerini periyodik olarak yürüten ana döngü."""
        while self._is_running:
            try:
                logging.debug("Senkronizasyon döngüsü başlıyor...")
                await self._run_sync_cycle()
                logging.debug(f"Senkronizasyon döngüsü tamamlandı. {SYNC_INTERVAL_SECONDS} saniye bekleniyor.")
            except Exception as e:
                logging.error(f"Senkronizasyon döngüsünde kritik hata: {e}", exc_info=False)
            
            try:
                await asyncio.sleep(SYNC_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
        
        logging.debug("SyncService döngüsü sonlandı.")

    async def _run_sync_cycle(self):
        """Tek bir senkronizasyon döngüsünü çalıştırır."""
        leader_adapter = await self.manager.get_adapter(self.leader_api_info)
        if not leader_adapter:
            logging.error("Senkronizasyon için lider adaptörü alınamadı.")
            return

        leader_positions = {p.symbol: p for p in await leader_adapter.get_positions()}
        leader_total_value = await leader_adapter.get_total_account_value_usdt()
        
        if not leader_total_value or leader_total_value <= 1.0:
            logging.error("Liderin toplam değeri alınamadı, senkronizasyon atlanıyor.")
            return

        followers_info = await load_api_keys_from_file(only_copy_trade_enabled=True)
        followers_info = [f for f in followers_info if f['user_id'] != self.leader_api_info.get('user_id')]

        tasks = [
            self._synchronize_follower(follower_info, leader_positions, leader_total_value)
            for follower_info in followers_info
        ]
        await asyncio.gather(*tasks)

    async def _synchronize_follower(self, follower_info: Dict, leader_positions: Dict, leader_total_value: float):
        """Tek bir takipçiyi liderle senkronize eder."""
        user_id = follower_info['user_id']
        log_prefix = f"[SYNC-FOLLOWER ({user_id})]"
        
        follower_adapter = await self.manager.get_adapter(follower_info)
        if not follower_adapter:
            logging.error(f"{log_prefix}: Adaptör alınamadı.")
            return

        try:
            follower_positions = {p.symbol: p for p in await follower_adapter.get_positions()}
            follower_total_value = await follower_adapter.get_total_account_value_usdt()
            if not follower_total_value or follower_total_value <= 1.0:
                logging.warning(f"{log_prefix}: Takipçi hesap değeri çok düşük, senkronizasyon atlanıyor.")
                return

            # A. Yetim pozisyonları kapat
            for symbol, pos in follower_positions.items():
                if symbol not in leader_positions:
                    logging.info(f"{log_prefix}: Yetim pozisyon '{symbol}' kapatılıyor...")
                    await follower_adapter.place_order(
                        symbol=symbol, order_type='market',
                        side='sell' if pos.side == 'long' else 'buy',
                        amount=pos.contracts, params={'reduceOnly': True}
                    )
            
            # B. Eksik pozisyonları aç (Geç Katılım)
            for symbol, leader_pos in leader_positions.items():
                if symbol not in follower_positions:
                    if await self._should_late_join(leader_pos, follower_adapter):
                        logging.info(f"{log_prefix}: Eksik pozisyon '{symbol}' için geç katılım yapılıyor...")
                        
                        leader_intended_leverage = leader_pos.leverage
                        await follower_adapter.set_leverage(leader_pos.symbol, leader_pos.leverage)
                        
                        calc_result = await calculate_follower_amount(
                            follower_adapter=follower_adapter,
                            leader_position=leader_pos,
                            follower_total_value=follower_total_value,
                            leader_total_value=leader_total_value,
                            leader_intended_leverage=leader_intended_leverage
                        )

                        if calc_result and calc_result.get("amount", 0) > 0:
                            follower_amount = calc_result["amount"]
                            follower_leverage = calc_result["leverage"]

                            await follower_adapter.set_leverage(leader_pos.symbol, follower_leverage)
                            
                            order_side = 'buy' if leader_pos.side == 'long' else 'sell'
                            

                            await follower_adapter.place_order(
                                symbol=leader_pos.symbol,
                                order_type='market',
                                side=order_side,
                                amount=follower_amount
                            )
                            logging.debug(f"{log_prefix}: Geç katılım emri gönderildi. Sembol: {symbol}, Yön: {order_side}, Miktar: {follower_amount}, Kaldıraç: {follower_leverage}x")
                        else:
                            logging.warning(f"{log_prefix}: Geç katılım için hesaplanan miktar ({calc_result}) geçersiz.")

        except Exception as e:
            logging.error(f"{log_prefix}: Senkronizasyon sırasında hata: {e}", exc_info=False)

    async def _should_late_join(self, leader_pos: Position, follower_adapter: ExchangeAdapterInterface) -> bool:
        """Bir pozisyona geç katılıp katılınmayacağına karar verir."""
        try:
            # 1. Fiyat farkı kontrolü
            ticker = await follower_adapter.get_ticker(leader_pos.symbol)
            current_price = float(ticker.get('last'))
            price_change = abs((current_price - leader_pos.entry_price) / leader_pos.entry_price)

            if price_change > (LATE_JOIN_MAX_PRICE_CHANGE_PERCENT / 100.0):
                logging.debug(f"Geç katılım reddedildi ({leader_pos.symbol}): Fiyat farkı çok yüksek ({price_change:.2%})")
                return False
            
            # 2. Pozisyon yaşı kontrolü
            if leader_pos.timestamp_ms:
                pos_age_seconds = (datetime.now(timezone.utc).timestamp() * 1000 - leader_pos.timestamp_ms) / 1000
                if pos_age_seconds > LATE_JOIN_MAX_AGE_MINUTES * 60:
                    logging.debug(f"Geç katılım reddedildi ({leader_pos.symbol}): Pozisyon çok eski ({pos_age_seconds/60:.1f} dakika).")
                    return False
            
            return True
        except Exception as e:
            logging.error(f"Geç katılım kontrolü sırasında hata ({leader_pos.symbol}): {e}")
            return False