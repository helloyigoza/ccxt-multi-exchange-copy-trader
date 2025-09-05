# exchange/services/replication_service.py

import logging
import asyncio
from typing import Dict, Any, Optional

from ..core.exchange_manager import ExchangeManager
from ..models.order import Order
from ..models.position import Position
from ..utils.helpers import load_api_keys_from_file, format_symbol_for_ccxt
from ..utils.calculator import calculate_follower_amount

class ReplicationService:
    """
    Başarılı lider işlemlerini aktif takipçilere ANINDA kopyalamaktan sorumlu servis.
    """
    def __init__(self, exchange_manager: ExchangeManager):
        self.manager = exchange_manager
        logging.debug("ReplicationService başlatıldı.")

    async def replicate_action(
        self,
        leader_api_info: Dict[str, Any],
        leader_order: Order,
    ) -> Dict[str, Any]:
        log_prefix = f"REPLICATE ({leader_order.symbol} {leader_order.side} {leader_order.amount})"
        logging.debug(f"{log_prefix}: Anlık kopyalama işlemi başlatıldı.")

        followers = await load_api_keys_from_file(only_copy_trade_enabled=True)
        followers = [f for f in followers if f['user_id'] != leader_api_info.get('user_id')]

        if not followers:
            logging.debug(f"{log_prefix}: Aktif takipçi bulunamadı, kopyalama atlanıyor.")
            return {"status": "no_followers", "processed_count": 0}

        leader_adapter = await self.manager.get_adapter(leader_api_info)
        if not leader_adapter:
            logging.critical(f"{log_prefix}: Lider adaptörü alınamadı. Kopyalama iptal edildi.")
            return {"status": "error", "message": "Lider adaptörü alınamadı."}
        
        leader_total_value = await leader_adapter.get_total_account_value_usdt()
        if not leader_total_value or leader_total_value <= 1.0:
            logging.critical(f"{log_prefix}: Liderin toplam hesap değeri alınamadı. Kopyalama iptal edildi.")
            return {"status": "error", "message": "Lider hesap değeri alınamadı."}
        
        # ### DÜZELTME: Pozisyon Kapatma ve Kaldıraç Mantığı ###
        leader_positions = {p.symbol: p for p in await leader_adapter.get_positions()}
        leader_symbol_clean = format_symbol_for_ccxt(leader_order.symbol)
        leader_pos_to_replicate = leader_positions.get(leader_symbol_clean)

        # raw_data içindeki params'dan reduceOnly kontrolü daha güvenilir olabilir
        is_reduce_only = leader_order.raw_data.get('info', {}).get('reduceOnly', False) or leader_order.raw_data.get('params', {}).get('reduceOnly', False)

        if not leader_pos_to_replicate:
            if is_reduce_only:
                logging.info(f"{log_prefix}: Lider pozisyonu ({leader_symbol_clean}) tamamen kapatıldı (artık mevcut değil). Takipçi pozisyonları kapatılacak.")
                # Bu bir kapatma emri. Takipçiye sinyal göndermek için bir "yer tutucu" (placeholder) pozisyon nesnesi oluştur.
                leader_pos_to_replicate = Position(
                    symbol=leader_symbol_clean,
                    side='long' if leader_order.side == 'sell' else 'short', # Kapanış emrinin tersi yönü
                    contracts=0, # Pozisyon kalmadı
                    entry_price=leader_order.average_price or 0,
                    mark_price=leader_order.average_price or 0,
                    leverage=1, # Önemli değil
                    unrealized_pnl=0,
                    # Bu özel durumu belirtmek için raw_data'ya bir bayrak ekle
                    raw_data={'is_placeholder_for_close': True, 'closed_amount': leader_order.filled}
                )
            else:
                logging.error(f"{log_prefix}: Liderin güncel pozisyonu ({leader_symbol_clean}) bulunamadı. Kopyalama iptal edildi. Mevcut pozisyonlar: {list(leader_positions.keys())}")
                return {"status": "error", "message": f"Liderin pozisyonu ({leader_symbol_clean}) bulunamadı."}

        tasks = [
            self._replicate_for_single_follower(
                follower_api_info,
                leader_order,
                leader_pos_to_replicate,
                leader_total_value
            )
            for follower_api_info in followers
        ]
        
        results = await asyncio.gather(*tasks)

        summary = {
            "status": "completed",
            "total_followers": len(followers),
            "successful": sum(1 for r in results if r.get("status") == "success"),
            "failed": sum(1 for r in results if r.get("status") == "failed"),
            "skipped": sum(1 for r in results if r.get("status") == "skipped"),
            "details": results
        }
        logging.info(f"{log_prefix}: Kopyalama tamamlandı. Başarılı: {summary['successful']}, Hatalı: {summary['failed']}, Atlanan: {summary['skipped']}")
        
        return summary

    async def _replicate_for_single_follower(
        self,
        follower_api_info: Dict[str, Any],
        leader_order: Order,
        leader_position: Position,
        leader_total_value: float
    ) -> Dict[str, Any]:
        user_id = follower_api_info.get("user_id")
        log_prefix = f"[REPLICATE-FOLLOWER ({user_id} - {leader_order.symbol})]"
        
        follower_adapter = await self.manager.get_adapter(follower_api_info)
        if not follower_adapter:
            logging.error(f"{log_prefix}: Adaptör oluşturulamadı.")
            return {"user_id": user_id, "status": "failed", "reason": "Adaptör oluşturulamadı."}
        
        try:
            follower_total_value = await follower_adapter.get_total_account_value_usdt()
            if not follower_total_value or follower_total_value <= 1.0:
                logging.warning(f"{log_prefix}: Hesap değeri ({follower_total_value}) çok düşük, atlanıyor.")
                return {"user_id": user_id, "status": "skipped", "reason": "Takipçi hesap değeri çok düşük."}

            is_reduce_only = leader_order.raw_data.get('info', {}).get('reduceOnly', False) or leader_order.raw_data.get('params', {}).get('reduceOnly', False)
            
            # ### YENİ ### Liderin AI komutundan gelen niyetini al
            # Komut, order objesinin raw_data'sına eklenmiş olmalı.
            leader_command = leader_order.raw_data.get('command_details', {})
            leader_intended_leverage = leader_command.get('leverage', leader_position.leverage) # Komutta yoksa pozisyondan al


            follower_params = {}
            follower_amount = 0.0
            order_side = leader_order.side

            # ### DÜZELTME: Kapatma / Azaltma Mantığı ###
            if is_reduce_only:
                logging.debug(f"{log_prefix}: Pozisyon azaltma/kapatma işlemi.")
                follower_params['reduceOnly'] = True
                order_side = 'sell' if leader_position.side == 'long' else 'buy'

                follower_positions = {p.symbol: p for p in await follower_adapter.get_positions()}
                follower_pos = follower_positions.get(leader_position.symbol)

                if not follower_pos:
                    logging.warning(f"{log_prefix}: Lider pozisyon azaltırken takipçinin açık pozisyonu bulunamadı, atlanıyor.")
                    return {"user_id": user_id, "status": "skipped", "reason": "Azaltılacak pozisyon bulunamadı."}

                if leader_position.raw_data.get('is_placeholder_for_close'):
                    # Bu, lider pozisyonunun tamamen kapatıldığı anlamına gelir.
                    logging.info(f"{log_prefix}: Lider pozisyonu tamamen kapattı. Takipçinin pozisyonu da tamamen kapatılacak.")
                    follower_amount = follower_pos.contracts
                else: # Bu, kısmi bir kapatmadır.
                    original_leader_contracts = leader_position.contracts + leader_order.filled
                    if original_leader_contracts < 1e-9:
                         return {"user_id": user_id, "status": "failed", "reason": "Liderin orijinal pozisyon büyüklüğü sıfır."}
                    
                    percentage_to_close = leader_order.filled / original_leader_contracts
                    logging.info(f"{log_prefix}: Lider pozisyonunun %{percentage_to_close * 100:.2f} kadarını kapattı. Takipçiye uygulanıyor.")
                    follower_amount = follower_pos.contracts * percentage_to_close
            
            # ### YENİ: Açma / Artırma Mantığı ###
            else:
                logging.debug(f"{log_prefix}: Pozisyon açma/artırma işlemi.")
                
                # Yeni hesaplama fonksiyonunu çağır
                calc_result = await calculate_follower_amount(
                    follower_adapter=follower_adapter,
                    leader_position=leader_position,
                    follower_total_value=follower_total_value,
                    leader_total_value=leader_total_value,
                    leader_intended_leverage=leader_intended_leverage,
                )

                if not calc_result:
                    logging.warning(f"{log_prefix}: Miktar hesaplanamadı, işlem atlanıyor.")
                    return {"user_id": user_id, "status": "skipped", "reason": "Miktar hesaplama başarısız."}
                
                follower_amount = calc_result['amount']
                follower_leverage = calc_result['leverage']

                # İşlemden hemen önce kaldıracı ayarla
                await follower_adapter.set_leverage(leader_position.symbol, follower_leverage)
                logging.info(f"{log_prefix}: Kaldıraç {follower_leverage}x olarak ayarlandı.")


            if follower_amount is None or follower_amount <= 0:
                logging.warning(f"{log_prefix}: Hesaplanan miktar ({follower_amount}) geçersiz, atlanıyor.")
                return {"user_id": user_id, "status": "skipped", "reason": f"Hesaplanan miktar geçersiz: {follower_amount}"}

            # Son miktarı borsa hassasiyetine göre tekrar normalize et (özellikle kapatma durumları için)
            final_follower_amount = await follower_adapter.normalize_amount(leader_order.symbol, follower_amount)
            
            follower_order = await follower_adapter.place_order(
                symbol=leader_order.symbol,
                order_type='market', # Kopyalama her zaman market emriyle yapılır
                side=order_side,
                amount=final_follower_amount,
                params=follower_params
            )

            if follower_order.status == 'failed':
                logging.error(f"{log_prefix}: Emir gönderilemedi. Sebep: {follower_order.error_message}")
                return {"user_id": user_id, "status": "failed", "reason": follower_order.error_message}
            
            logging.info(f"{log_prefix}: Kopyalama emri başarıyla gönderildi. Miktar: {follower_order.amount}, Emir ID: {follower_order.id}")
            return {"user_id": user_id, "status": "success", "order_id": follower_order.id, "amount": follower_order.filled}

        except Exception as e:
            logging.error(f"{log_prefix}: Kopyalama sırasında beklenmedik hata: {e}", exc_info=True)
            return {"user_id": user_id, "status": "failed", "reason": f"Genel Hata: {str(e)}"}